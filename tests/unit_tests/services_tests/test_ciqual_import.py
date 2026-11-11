import gzip
from pathlib import Path

import httpx
import pytest

from mealie.services.recipe.ciqual_import import (
    ALIM_FILE,
    COMPO_FILE,
    CiqualDataverseClient,
    CiqualImportError,
    parse_ciqual,
    parse_dataset_url,
    read_dataset_info,
)

ALIM_XML = """<?xml version="1.0" encoding="windows-1252"?>
<TABLE>
<ALIM>
<alim_code> 13028 </alim_code>
<alim_nom_fr> Pomme, pulpe et peau, crue </alim_nom_fr>
<alim_nom_eng> Apple, pulp and peel, raw </alim_nom_eng>
<alim_grp_code> 02 </alim_grp_code>
</ALIM>
<ALIM>
<alim_code> 2000 </alim_code>
<alim_nom_fr> Citron, pulpe, cru </alim_nom_fr>
<alim_nom_eng> Lemon, pulp, raw </alim_nom_eng>
<alim_grp_code> 02 </alim_grp_code>
</ALIM>
<ALIM>
<alim_code> 3000 </alim_code>
<alim_nom_fr> Lait infantile </alim_nom_fr>
<alim_nom_eng> Infant formula </alim_nom_eng>
<alim_grp_code> 11 </alim_grp_code>
</ALIM>
<ALIM>
<alim_code> 4000 </alim_code>
<alim_nom_fr> Aliment sans énergie </alim_nom_fr>
<alim_nom_eng />
<alim_grp_code> 02 </alim_grp_code>
</ALIM>
</TABLE>
"""


def _compo(code: str, const: str, value: str) -> str:
    return f"<COMPO><alim_code> {code} </alim_code><const_code> {const} </const_code><teneur> {value} </teneur></COMPO>"


COMPO_XML = (
    '<?xml version="1.0" encoding="windows-1252"?>\n<TABLE>\n'
    + "\n".join(
        [
            _compo("13028", "328", "54,2"),
            _compo("13028", "31000", "11,6"),
            _compo("13028", "32000", "traces"),
            _compo("13028", "10110", "&lt; 0,5"),
            _compo("2000", "333", "33"),
            _compo("2000", "25000", "-"),
            _compo("3000", "328", "70"),
            _compo("4000", "31000", "1"),
        ]
    )
    + "\n</TABLE>\n"
)

DATASET_URL = "https://data.example.org/dataset.xhtml?persistentId=doi:10.57745/TEST"


def _dataset(files: list[tuple[int, str]]) -> dict:
    return {
        "status": "OK",
        "data": {
            "latestVersion": {
                "versionNumber": 3,
                "versionMinorNumber": 1,
                "releaseTime": "2025-11-14T10:00:00Z",
                "files": [{"label": label, "dataFile": {"id": file_id, "filename": label}} for file_id, label in files],
            }
        },
    }


@pytest.fixture()
def xml_files(tmp_path: Path) -> tuple[Path, Path]:
    alim, compo = tmp_path / "alim.xml", tmp_path / "compo.xml"
    alim.write_bytes(ALIM_XML.encode("cp1252"))
    compo.write_bytes(COMPO_XML.encode("cp1252"))
    return alim, compo


def test_parse_ciqual(xml_files: tuple[Path, Path]):
    foods = parse_ciqual(*xml_files)

    # sorted by code, without the infant foods nor the foods without energy
    assert [food.code for food in foods] == ["2000", "13028"]
    lemon, apple = foods
    assert apple.name == "Pomme, pulpe et peau, crue"
    assert apple.name_en == "Apple, pulp and peel, raw"
    assert apple.group_code == "02"
    assert apple.nutrients["calories"] == 54.2
    assert apple.nutrients["carbohydrate_content"] == 11.6
    assert apple.nutrients["sugar_content"] == 0.0
    assert apple.nutrients["sodium_content"] == 0.25
    assert lemon.nutrients["calories"] == 33.0
    assert lemon.nutrients["protein_content"] is None


@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi:10.57745/RDMHWY",
            ("https://entrepot.recherche.data.gouv.fr", "doi:10.57745/RDMHWY"),
        ),
        (
            " https://data.example.org/api/datasets/:persistentId/?persistentId=doi:1/X&version=2 ",
            ("https://data.example.org", "doi:1/X"),
        ),
    ],
)
def test_parse_dataset_url(url: str, expected: tuple[str, str]):
    location = parse_dataset_url(url)
    assert (location.base_url, location.persistent_id) == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi:10.57745/RDMHWY",
        "https://entrepot.recherche.data.gouv.fr/dataset.xhtml",
        "not a url",
        "",
    ],
)
def test_parse_dataset_url_rejects(url: str):
    with pytest.raises(CiqualImportError):
        parse_dataset_url(url)


def test_read_dataset_info_picks_the_latest_files():
    info = read_dataset_info(
        _dataset(
            [
                (1, "alim_2020_07_07.xml"),
                (2, "alim_2025_11_03.xml"),
                (3, "alim_grp_2025_11_03.xml"),
                (4, "compo_2025_11_03.xml"),
                (5, "const_2025_11_03.xml"),
                (6, "Table Ciqual 2025_FR.xlsx"),
            ]
        )
    )

    assert info.version == "3.1"
    assert info.release_time == "2025-11-14T10:00:00Z"
    assert info.latest(ALIM_FILE).id == 2  # type: ignore[union-attr]
    assert info.latest(COMPO_FILE).id == 4  # type: ignore[union-attr]


def _transport(
    requests: list[httpx.Request], files: dict[int, bytes], dataset_status: int = 200
) -> httpx.MockTransport:
    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/datasets/:persistentId/":
            if dataset_status != 200:
                return httpx.Response(dataset_status)
            return httpx.Response(200, json=_dataset([(10, "alim_2025_11_03.xml"), (11, "compo_2025_11_03.xml")]))
        file_id = int(request.url.path.rsplit("/", 1)[-1])
        return httpx.Response(200, content=files[file_id]) if file_id in files else httpx.Response(404)

    return httpx.MockTransport(respond)


def test_fetch_downloads_and_parses_the_latest_table():
    requests: list[httpx.Request] = []
    files = {10: ALIM_XML.encode("cp1252"), 11: COMPO_XML.encode("cp1252")}
    download = CiqualDataverseClient(_transport(requests, files)).fetch(DATASET_URL)

    assert [food.code for food in download.foods] == ["2000", "13028"]
    assert download.version == "3.1"
    assert download.release_time == "2025-11-14T10:00:00Z"
    assert download.table_version == "2025-11-03"
    assert requests[0].url.params["persistentId"] == "doi:10.57745/TEST"
    assert [r.url.path for r in requests[1:]] == ["/api/access/datafile/10", "/api/access/datafile/11"]


@pytest.mark.parametrize(
    "files, dataset_status, message",
    [
        ({10: ALIM_XML.encode("cp1252"), 11: COMPO_XML.encode("cp1252")}, 503, "could not be read"),
        ({10: ALIM_XML.encode("cp1252")}, 200, "could not be downloaded"),
        ({10: b"<TABLE><ALIM>", 11: COMPO_XML.encode("cp1252")}, 200, "could not be read"),
        ({10: gzip.compress(b"<TABLE/>"), 11: b"<TABLE/>"}, 200, "Ciqual"),
    ],
)
def test_fetch_errors(files: dict[int, bytes], dataset_status: int, message: str):
    with pytest.raises(CiqualImportError, match=message):
        CiqualDataverseClient(_transport([], files, dataset_status)).fetch(DATASET_URL)
