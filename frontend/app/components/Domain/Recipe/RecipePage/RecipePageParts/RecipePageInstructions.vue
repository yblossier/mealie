<template>
  <section @keyup.ctrl.z="undoMerge">
    <!-- Ingredient Link Editor -->
    <BaseDialog
      v-model="dialog"
      :title="$t('recipe.link-references')"
      :icon="$globals.icons.link"
      width="100%"
      max-width="600px"
      max-height="60%"
    >
      <div class="grid">
        <div class="sticky">
          <v-card flat style="max-height: 40dvh; overflow-y: auto;">
            <v-card-text class="pt-4">
              <p>
                {{ activeDialogStepText }}
              </p>
            </v-card-text>
          </v-card>
          <v-divider />
        </div>
        <v-card flat>
          <v-card-text>
            <p v-if="!linkBlocks.length" class="text-body-medium text-medium-emphasis">
              {{ $t("recipe.no-references-to-link") }}
            </p>
            <div
              v-for="(block, blockIndex) in linkBlocks"
              :key="block.key"
              :data-testid="`link-block-${block.key}`"
            >
              <v-divider v-if="blockIndex > 0" class="my-4" />
              <h3 class="link-block-title ml-1 mb-1">
                {{ $t(block.titleKey, block.count) }}
              </h3>
              <div
                v-for="group in block.groups"
                :key="group.key"
                class="ml-2"
              >
                <h4 v-if="group.label" class="link-step-title ml-1 mt-3">
                  {{ group.label }}
                </h4>
                <template v-if="group.ingredients.length">
                  <h5 class="link-type-title ml-3 mt-2">
                    {{ $t("recipe.ingredients") }}
                  </h5>
                  <template v-for="section in group.ingredients" :key="section.title">
                    <div v-if="section.title" class="link-section-title ml-5 mt-1">
                      {{ section.title }}
                    </div>
                    <v-checkbox-btn
                      v-for="ing in section.ingredients"
                      :key="ing.referenceId"
                      v-model="activeRefs"
                      :value="ing.referenceId"
                      class="ml-4"
                    >
                      <template #label>
                        <RecipeIngredientHtml :ingredient="ing" :scale="scale" />
                      </template>
                    </v-checkbox-btn>
                  </template>
                </template>
                <template v-if="group.tools.length">
                  <h5 class="link-type-title ml-3 mt-2">
                    {{ $t("tool.tools") }}
                  </h5>
                  <v-checkbox-btn
                    v-for="tool in group.tools"
                    :key="tool.id"
                    v-model="activeToolReferenceIds"
                    :value="tool.id"
                    class="ml-4"
                  >
                    <template #label>
                      <v-icon size="18" class="mr-2">
                        {{ toolCategoryIcon(tool.category) }}
                      </v-icon>
                      {{ tool.name }}
                    </template>
                  </v-checkbox-btn>
                </template>
                <template v-if="group.notes.length">
                  <h5 class="link-type-title ml-3 mt-2">
                    {{ $t("recipe.notes") }}
                  </h5>
                  <v-checkbox-btn
                    v-for="note in group.notes"
                    :key="note.referenceId"
                    v-model="activeNoteReferenceIds"
                    :value="note.referenceId"
                    class="ml-4"
                  >
                    <template #label>
                      {{ note.title || $t('recipe.note') }}
                    </template>
                  </v-checkbox-btn>
                </template>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <v-divider />

      <template #card-actions>
        <div class="d-flex align-center flex-grow-1">
          <BaseButton
            cancel
            @click="closeDialog"
          />
          <v-spacer />
          <div class="d-flex flex-wrap align-center justify-end ga-2">
            <BaseButton
              color="info"
              @click="autoSetReferences"
            >
              <template #icon>
                {{ $globals.icons.robot }}
              </template>
              {{ $t("recipe.auto") }}
            </BaseButton>
            <BaseButton
              save
              @click="saveDialogLinks"
            />
            <BaseButton
              v-if="availableDialogNextStep"
              @click="saveAndOpenNextDialogLinks"
            >
              <template #icon>
                {{ $globals.icons.forward }}
              </template>
              {{ $t("recipe.nextStep") }}
            </BaseButton>
          </div>
        </div>
      </template>
    </BaseDialog>

    <div
      class="d-flex"
      :class="[isMobile ? 'flex-column ga-2' : 'justify-space-between', { 'cook-mode-actions': isCookMode }]"
    >
      <h2
        v-if="!isCookMode"
        class="mt-1 text-headline-small font-weight-medium opacity-80"
      >
        {{ $t("recipe.instructions") }}
      </h2>
      <div
        v-if="!isEditForm"
        class="d-flex align-center ga-2"
        :class="isMobile ? 'justify-center' : 'ml-auto'"
      >
        <template v-if="thermomixRecipe">
          <v-btn
            v-if="isMobile"
            tag="div"
            class="thermomix-icon-toggle thermomix-toggle--static"
            variant="flat"
            readonly
            :ripple="false"
            role="img"
            aria-disabled="true"
            :aria-label="$t('recipe.thermomix.recipe-for')"
            :title="$t('recipe.thermomix.recipe-for')"
            data-testid="thermomix-recipe-badge"
          >
            <img
              src="/thermomix-icon.png"
              alt=""
              class="thermomix-icon-toggle__image"
            >
          </v-btn>
          <v-btn
            v-else
            tag="div"
            class="thermomix-toggle thermomix-toggle--static"
            variant="outlined"
            readonly
            :ripple="false"
            role="img"
            aria-disabled="true"
            :aria-label="$t('recipe.thermomix.recipe-for')"
            :title="$t('recipe.thermomix.recipe-for')"
            data-testid="thermomix-recipe-badge"
          >
            <span class="d-flex flex-column align-center">
              <span class="thermomix-toggle__label">{{ $t("recipe.thermomix.recipe-for-label") }}</span>
              <img
                src="/thermomix-logo.png"
                alt=""
                class="thermomix-toggle__logo"
              >
            </span>
          </v-btn>
        </template>
        <v-btn
          v-else-if="isMobile"
          class="thermomix-icon-toggle"
          :class="{ 'thermomix-icon-toggle--active': showThermomix }"
          variant="flat"
          :aria-pressed="showThermomix"
          :aria-label="showThermomix ? $t('recipe.thermomix.back-to-steps') : $t('recipe.thermomix.view')"
          :title="showThermomix ? $t('recipe.thermomix.back-to-steps') : $t('recipe.thermomix.view')"
          data-testid="thermomix-icon-toggle"
          @click="toggleThermomixView()"
        >
          <img
            src="/thermomix-icon.png"
            alt="Thermomix"
            class="thermomix-icon-toggle__image"
          >
        </v-btn>
        <v-btn
          v-else
          class="thermomix-toggle"
          :class="{ 'thermomix-toggle--active': showThermomix }"
          variant="outlined"
          :color="showThermomix ? 'success' : undefined"
          :aria-pressed="showThermomix"
          :title="showThermomix ? $t('recipe.thermomix.back-to-steps') : $t('recipe.thermomix.view')"
          @click="toggleThermomixView()"
        >
          <span class="d-flex flex-column align-center">
            <span class="thermomix-toggle__label">{{ $t("recipe.thermomix.view-label") }}</span>
            <img
              src="/thermomix-logo.png"
              alt="Thermomix"
              class="thermomix-toggle__logo"
            >
          </span>
        </v-btn>
        <BaseButton
          v-if="!isCookMode"
          color="primary"
          class="cook-mode-button"
          @click="toggleCookMode()"
        >
          <template #icon>
            {{ $globals.icons.primary }}
          </template>
          {{ $t("recipe.cook-mode") }}
        </BaseButton>
      </div>
    </div>
    <RecipePageThermomixView
      v-if="thermomixActive"
      class="mt-4"
      :recipe="recipe"
      :can-edit="canEditRecipe"
      :scale="scale"
      :ingredient-storage-key="ingredientStorageKey"
    />
    <v-bottom-sheet
      v-model="linkedNotesSheetOpen"
      max-width="900"
      inset
    >
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon size="20" class="mr-2">
            {{ $globals.icons.noteTextOutline }}
          </v-icon>
          {{ $t('recipe.linked-notes-with-count', { count: activeStepLinkedNotes.length }) }}
          <v-spacer />
          <v-btn
            icon
            variant="text"
            density="comfortable"
            :aria-label="$t('general.close')"
            @click="linkedNotesSheetOpen = false"
          >
            <v-icon>{{ $globals.icons.close }}</v-icon>
          </v-btn>
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <template
            v-for="(note, noteIndex) in activeStepLinkedNotes"
            :key="note.referenceId ?? note.title"
          >
            <v-divider
              v-if="noteIndex > 0"
              class="my-3"
            />
            <div class="text-title-large mb-1">
              {{ note.title || $t('recipe.note') }}
            </div>
            <SafeMarkdown :source="note.text" />
          </template>
        </v-card-text>
      </v-card>
    </v-bottom-sheet>
    <VueDraggable
      v-show="!thermomixActive"
      v-model="instructionList"
      :disabled="!isEditForm"
      handle=".handle"
      :delay="250"
      :delay-on-touch-only="true"
      v-bind="{
        animation: 200,
        group: 'recipe-instructions',
        ghostClass: 'ghost',
      }"
      @start="drag = true"
      @end="onDragEnd"
    >
      <TransitionGroup
        type="transition"
      >
        <BaseSwipeAction
          v-for="(step, index) in instructionList"
          :key="step.id!"
          class="list-group-item"
          :disabled="!isEditForm"
          :left-action="{ icon: $globals.icons.delete, label: $t('general.delete'), color: 'error' }"
          :right-action="{ icon: $globals.icons.link, label: $t('recipe.link-references'), color: 'primary' }"
          @swipe-left="instructionList.splice(index, 1)"
          @swipe-right="openReferenceDialog(index)"
        >
          <v-sheet
            v-if="step.id && showTitleEditor[step.id]"
            color="primary"
            class="mt-6 mb-2 d-flex align-center"
            :class="isEditForm ? 'pa-2' : 'pa-3'"
            style="border-radius: 6px; cursor: pointer; width: 100%;"
            @click="toggleCollapseSection(index)"
          >
            <template v-if="isEditForm">
              <v-text-field
                v-model="step.title"
                class="pa-0"
                density="compact"
                variant="solo"
                flat
                :placeholder="$t('recipe.section-title')"
                bg-color="primary"
                hide-details
                :autofocus="autofocusSectionId === step.id"
                @update:focused="onSectionTitleFocused(step.id, $event)"
              />
            </template>
            <template v-else>
              <v-toolbar-title class="section-title-text">
                {{ step.title }}
              </v-toolbar-title>
              <CookTime
                v-if="sectionTotalSeconds(index)"
                class="section-total-time ml-2 mr-1"
                :model-value="sectionTotalSeconds(index)"
                :is-edit-mode="false"
                :icon="$globals.icons.timerOutline"
                :label="$t('recipe.section-total-time')"
              />
            </template>
          </v-sheet>
          <v-hover v-slot="{ isHovering }">
            <v-card
              class="my-3"
              :class="[{ 'on-hover': isHovering }, { 'cursor-default': isEditForm }, isChecked(index)]"
              :elevation="isHovering ? 12 : 2"
              :ripple="false"
              @click="toggleDisabled(index)"
            >
              <v-card-title class="recipe-step-title pt-3" :class="!isChecked(index) ? 'pb-0' : 'pb-3'">
                <div class="d-flex align-center w-100">
                  <v-text-field
                    v-if="isEditForm"
                    v-model="step.summary"
                    class="headline"
                    hide-details
                    density="compact"
                    variant="solo"
                    flat
                    :placeholder="$t('recipe.step-index', { step: index + 1 })"
                  >
                    <template #prepend>
                      <v-icon size="26" class="handle">
                        {{ $globals.icons.arrowUpDown }}
                      </v-icon>
                    </template>
                  </v-text-field>
                  <div
                    v-else
                    class="summary-wrapper d-flex justify-space-between"
                  >
                    <template v-if="step.summary">
                      <SafeMarkdown
                        class="pr-2"
                        :source="step.summary"
                      />
                    </template>
                    <template v-else>
                      <span>
                        {{ $t('recipe.step-index', { step: index + 1 }) }}
                      </span>
                    </template>
                    <div class="step-times">
                      <CookTime
                        v-for="field in stepTimeFields"
                        :key="field.key"
                        :model-value="step[field.key] ?? null"
                        :is-edit-mode="false"
                        :icon="field.icon"
                        :label="field.label"
                      />
                    </div>
                  </div>
                  <template v-if="isEditForm">
                    <div class="ml-auto">
                      <BaseButtonGroup
                        :large="false"
                        :buttons="[
                          {
                            icon: $globals.icons.delete,
                            text: $t('general.delete'),
                            event: 'delete',
                          },
                          {
                            icon: $globals.icons.dotsVertical,
                            text: '',
                            event: 'open',
                            children: [
                              {
                                text: sectionTitleLabel(step.id),
                                event: 'toggle-section',
                              },
                              {
                                text: $t('recipe.link-references'),
                                event: 'link-references',
                              },
                              {
                                text: $t('recipe.upload-image'),
                                event: 'upload-image',
                              },
                              {
                                icon: previewStates[index] ? $globals.icons.edit : $globals.icons.eye,
                                text: previewStates[index] ? $t('recipe.edit-markdown') : $t('markdown-editor.preview-markdown-button-label'),
                                event: 'preview-step',
                                divider: true,
                              },
                              {
                                text: $t('recipe.merge-above'),
                                event: 'merge-above',
                              },
                              {
                                text: $t('recipe.move-to-top'),
                                event: 'move-to-top',
                              },
                              {
                                text: $t('recipe.move-to-bottom'),
                                event: 'move-to-bottom',
                              },
                              {
                                text: $t('recipe.insert-above'),
                                event: 'insert-above',
                              },
                              {
                                text: $t('recipe.insert-below'),
                                event: 'insert-below',
                              },
                            ],
                          },
                        ]"
                        @merge-above="mergeAbove(index - 1, index)"
                        @move-to-top="moveTo('top', index)"
                        @move-to-bottom="moveTo('bottom', index)"
                        @insert-above="insert(index)"
                        @insert-below="insert(index + 1)"
                        @toggle-section="toggleShowTitle(step.id!)"
                        @link-references="openReferenceDialog(index)"
                        @preview-step="togglePreviewState(index)"
                        @upload-image="openImageUpload(index)"
                        @delete="instructionList.splice(index, 1)"
                      />
                    </div>
                  </template>
                  <div v-if="!isEditForm" class="ml-auto d-flex align-center gap-1">
                    <v-btn
                      v-if="hasLinkedNotes(step) && !isCookMode"
                      variant="text"
                      icon
                      density="comfortable"
                      size="small"
                      @click.stop="openLinkedNotesSheet(step)"
                    >
                      <v-icon size="18">
                        {{ $globals.icons.noteTextOutline }}
                      </v-icon>
                      <v-tooltip activator="parent" location="top">
                        {{ $t('recipe.linked-notes-with-count', { count: linkedNotesForStep(step).length }) }}
                      </v-tooltip>
                    </v-btn>
                    <v-fade-transition>
                      <v-icon
                        v-show="isChecked(index)"
                        size="24"
                        color="success"
                      >
                        {{ $globals.icons.checkboxMarkedCircle }}
                      </v-icon>
                    </v-fade-transition>
                  </div>
                </div>
              </v-card-title>

              <v-progress-linear
                v-if="isEditForm && loadingStates[index]"
                :active="true"
                :indeterminate="true"
              />

              <!-- Content -->
              <DropZone
                @drop="(f) => handleImageDrop(index, f)"
                @drop-url="(u) => handleImageUrlDrop(index, u)"
                @drop-unsupported="notifyUnsupportedDrop"
              >
                <v-card-text
                  v-if="isEditForm"
                  @click="$emit('click-instruction-field', `${index}.text`)"
                >
                  <div
                    @mouseup="onStepTextSelect(index, $event)"
                    @keyup="onStepTextSelect(index, $event)"
                  >
                    <MarkdownEditor
                      v-model="instructionList[index]['text']"
                      v-model:preview="previewStates[index]"
                      class="mb-2"
                      :display-preview="false"
                      :textarea="{
                        hint: $t('recipe.attach-images-hint'),
                        persistentHint: true,
                      }"
                    />
                  </div>
                  <v-expand-transition>
                    <div
                      v-if="toolSelection && toolSelection.index === index"
                      class="mb-2"
                    >
                      <v-btn
                        size="small"
                        variant="tonal"
                        color="primary"
                        :loading="creatingTool"
                        data-testid="create-tool-from-selection"
                        @mousedown.prevent
                        @click="createToolFromSelection(step)"
                      >
                        <v-icon start>
                          {{ $globals.icons.potSteam }}
                        </v-icon>
                        {{ $t("recipe.create-tool-from-selection", { name: toolSelection.text }) }}
                      </v-btn>
                    </div>
                  </v-expand-transition>
                  <div
                    v-if="step.ingredientReferences && step.ingredientReferences.length"
                    class="linked-ingredients-editor pb-2"
                  >
                    <div
                      v-for="(linkRef, i) in step.ingredientReferences"
                      :key="linkRef.referenceId ?? i"
                      class="mb-1"
                    >
                      <RecipeIngredientHtml
                        v-if="linkRef.referenceId && ingredientLookup[linkRef.referenceId]"
                        :ingredient="ingredientLookup[linkRef.referenceId]"
                        :scale="scale"
                      />
                    </div>
                  </div>
                  <div
                    v-if="step.noteReferences && step.noteReferences.length"
                    class="linked-ingredients-editor mt-1"
                  >
                    <div
                      v-for="(noteRef, i) in step.noteReferences"
                      :key="noteRef.referenceId ?? i"
                      class="mb-1 d-flex align-center text-body-medium"
                    >
                      <v-icon size="14" class="mr-1" style="cursor: default;">
                        {{ $globals.icons.noteTextOutline }}
                      </v-icon>
                      {{ noteRef.referenceId != null ? (noteLookup[noteRef.referenceId] || $t('recipe.note')) : '' }}
                    </div>
                  </div>
                  <div
                    v-if="linkedToolsForStep(step).length"
                    class="linked-ingredients-editor mt-1"
                  >
                    <div
                      v-for="tool in linkedToolsForStep(step)"
                      :key="tool.id"
                      class="mb-1 d-flex align-center text-body-medium"
                    >
                      <v-icon size="14" class="mr-1" style="cursor: default;">
                        {{ toolCategoryIcon(tool.category) }}
                      </v-icon>
                      {{ tool.name }}
                    </div>
                  </div>
                  <v-autocomplete
                    v-if="stepReferenceOptions(index).length"
                    :model-value="stepReferenceIds(step)"
                    :items="stepReferenceOptions(index)"
                    :label="$t('recipe.uses-steps')"
                    :hint="$t('recipe.uses-steps-hint')"
                    :prepend-inner-icon="$globals.icons.sourceMerge"
                    data-testid="step-references-input"
                    class="mt-3 mb-4"
                    density="compact"
                    variant="outlined"
                    multiple
                    chips
                    closable-chips
                    clearable
                    persistent-hint
                    @update:model-value="setStepReferences(step, $event)"
                  />
                  <v-row dense class="mt-1">
                    <v-col
                      v-for="field in stepTimeFields"
                      :key="field.key"
                      cols="12"
                      sm="6"
                      md="3"
                    >
                      <CookTime
                        :model-value="step[field.key] ?? null"
                        :is-edit-mode="isEditForm"
                        :label="field.label"
                        :icon="field.icon"
                        @update:model-value="step[field.key] = $event"
                      />
                    </v-col>
                  </v-row>
                </v-card-text>
              </DropZone>

              <v-expand-transition>
                <div
                  v-if="!isChecked(index) && !isEditForm"
                  class="m-0 p-0"
                >
                  <v-card-text class="markdown">
                    <v-row>
                      <v-col
                        v-if="isCookMode && hasCookModeLinkedContent(step)"
                        cols="12"
                        sm="5"
                      >
                        <div
                          v-if="hasLinkedIngredients(step)"
                          class="ml-n4"
                        >
                          <RecipeIngredients
                            :value="recipe.recipeIngredient.filter((ing) => {
                              if (!step.ingredientReferences) return false
                              return step.ingredientReferences.map((ref) => ref.referenceId).includes(ing.referenceId || '')
                            })"
                            :scale="scale"
                            :is-cook-mode="isCookMode"
                            :storage-key="ingredientStorageKey"
                            :recipe-id="recipe.id"
                          />
                        </div>
                        <v-divider
                          v-if="hasLinkedIngredients(step) && hasLinkedNotes(step)"
                          class="my-3"
                        />
                        <div v-if="hasLinkedNotes(step)">
                          <template
                            v-for="(note, noteIndex) in linkedNotesForStep(step)"
                            :key="note.referenceId ?? note.title"
                          >
                            <v-divider
                              v-if="noteIndex > 0"
                              class="my-3"
                            />
                            <div class="text-title-large mb-1">
                              {{ note.title || $t('recipe.note') }}
                            </div>
                            <SafeMarkdown :source="note.text" />
                          </template>
                        </div>
                      </v-col>
                      <v-divider
                        v-if="isCookMode && hasCookModeLinkedContent(step) && $vuetify.display.smAndUp"
                        vertical
                      />
                      <v-col>
                        <div
                          v-if="usedStepsForStep(step).length"
                          class="step-uses d-flex flex-wrap align-center ga-2 mb-2"
                          data-testid="step-uses"
                        >
                          <span class="text-body-medium text-medium-emphasis d-flex align-center">
                            <v-icon size="16" class="mr-1">
                              {{ $globals.icons.sourceMerge }}
                            </v-icon>
                            {{ $t('recipe.uses-steps') }}
                          </span>
                          <v-chip
                            v-for="used in usedStepsForStep(step)"
                            :key="used.id"
                            size="small"
                            variant="tonal"
                            color="primary"
                          >
                            {{ used.label }}
                          </v-chip>
                        </div>
                        <SafeMarkdown
                          class="markdown"
                          :source="stepSource(step.text)"
                        />
                        <div
                          v-if="linkedToolsForStep(step).length"
                          class="step-tools d-flex flex-wrap ga-2 mt-2"
                        >
                          <v-chip
                            v-for="tool in linkedToolsForStep(step)"
                            :key="tool.id"
                            size="small"
                            variant="tonal"
                            :prepend-icon="toolCategoryIcon(tool.category)"
                          >
                            {{ tool.name }}
                          </v-chip>
                        </div>
                      </v-col>
                    </v-row>
                  </v-card-text>
                </div>
              </v-expand-transition>
            </v-card>
          </v-hover>
        </BaseSwipeAction>
      </TransitionGroup>
    </VueDraggable>
    <v-divider
      v-if="!isCookMode"
      class="mt-10 d-flex d-md-none"
    />
  </section>
</template>

<script setup lang="ts">
import { VueDraggable } from "vue-draggable-plus";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import type { RecipeStep, RecipeNote, RecipeIngredient, RecipeAsset, RecipeOut, ToolOut } from "~/lib/api/types/recipe";
import { uuid4 } from "~/composables/use-utils";
import { useUserApi, useStaticRoutes } from "~/composables/api";
import { usePageState, usePageUser } from "~/composables/recipe-page/shared-state";
import { useExtractIngredientReferences } from "~/composables/recipe-page/use-extract-ingredient-references";
import DropZone from "~/components/global/DropZone.vue";
import { alert } from "~/composables/use-toast";
import RecipeIngredients from "~/components/Domain/Recipe/RecipeIngredients.vue";
import RecipeIngredientHtml from "~/components/Domain/Recipe/RecipeIngredientHtml.vue";
import { mergeSteps, undoStepMerge, type StepMerge } from "~/lib/recipe/instruction-merge";
import { toolCategoryIcon, toolsMentionedIn } from "~/lib/recipe/tool-display";
import { isThermomixRecipe, tagThermomixSettings } from "~/lib/recipe/thermomix-settings";
import CookTime from "./CookTime.vue";
import RecipePageThermomixView from "./RecipePageThermomixView.vue";
import { useRecipePermissions } from "~/composables/recipes";
import { allStepsDone, useMadeThisPrompt } from "~/composables/recipes/use-made-this-prompt";
import type { HouseholdSummary } from "~/lib/api/types/household";

const instructionList = defineModel<RecipeStep[]>("modelValue", { required: true, default: () => [] });
const assets = defineModel<RecipeAsset[]>("assets", { required: true, default: () => [] });

const props = defineProps({
  recipe: {
    type: Object as () => RecipeOut,
    required: true,
  },
  scale: {
    type: Number,
    default: 1,
  },
  ingredientStorageKey: {
    type: String,
    default: undefined,
  },
  /**
   * The recipe page mounts one instance per layout (page, cook mode); only the visible one loads the Thermomix view.
   */
  active: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(["click-instruction-field", "update:assets"]);

const i18n = useI18n();
const { isCookMode, toggleCookMode, isEditForm, isThermomixView: showThermomix, toggleThermomixView }
  = usePageState(props.recipe.slug);
const { extractIngredientReferences } = useExtractIngredientReferences();

// Recipes already written for the Thermomix (Cookomix, or flagged as such) show their settings in place, without a Thermomix view
const thermomixRecipe = computed(() => isThermomixRecipe(props.recipe));
const thermomixActive = computed(() =>
  showThermomix.value && !thermomixRecipe.value && !isEditForm.value && props.active,
);

function stepSource(text: string): string {
  return thermomixRecipe.value ? tagThermomixSettings(text) : text;
}

const display = useDisplay();
const isMobile = computed(() => display.xs.value);

const { user } = usePageUser();
const recipeHousehold = ref<HouseholdSummary>();
if (user) {
  useUserApi().households.getOne(props.recipe.householdId).then(({ data }) => {
    recipeHousehold.value = data || undefined;
  });
}
const { canEditRecipe } = useRecipePermissions(props.recipe, recipeHousehold, user);

const dialog = ref(false);
const disabledSteps = ref<number[]>([]);

const showTitleEditor = ref<{ [key: string]: boolean }>({});
// set when a section is opened from the toolbar, cleared once its field takes focus, so that
// scrolling an already-open section back into view does not pull focus again
const autofocusSectionId = ref<string | null>(null);

// ===============================================================
// UI State Helpers

function hasSectionTitle(title: string | undefined) {
  return !(title === null || title === "" || title === undefined);
}

watch(instructionList, (v) => {
  disabledSteps.value = [];

  v.forEach((element: RecipeStep) => {
    // Only derive visibility for steps we have not seen yet. This watcher is deep, so it also
    // fires while the user is typing a section title, and re-deriving would close the editor
    // the moment they cleared the text they had just entered.
    if (element.id !== undefined && !(element.id in showTitleEditor.value)) {
      showTitleEditor.value[element.id] = hasSectionTitle(element.title!);
    }
  });
}, { deep: true });

const showCookMode = ref(false);

onMounted(() => {
  instructionList.value.forEach((element: RecipeStep) => {
    if (element.id !== undefined) {
      showTitleEditor.value[element.id!] = hasSectionTitle(element.title!);
    }

    if (showCookMode.value === false && element.ingredientReferences && element.ingredientReferences.length > 0) {
      showCookMode.value = true;
    }

    showTitleEditor.value = { ...showTitleEditor.value };
  });

  if (assets.value === undefined) {
    emit("update:assets", []);
  }
});

function toggleDisabled(stepIndex: number) {
  if (isEditForm.value) {
    return;
  }
  if (disabledSteps.value.includes(stepIndex)) {
    const index = disabledSteps.value.indexOf(stepIndex);
    if (index !== -1) {
      disabledSteps.value.splice(index, 1);
    }
  }
  else {
    disabledSteps.value.push(stepIndex);
  }
}

function isChecked(stepIndex: number) {
  if (disabledSteps.value.includes(stepIndex) && !isEditForm.value) {
    return "disabled-card";
  }
}

// Once every step is checked off, offer to record the cook in the recipe's timeline
const madeThisPrompt = useMadeThisPrompt(props.recipe.slug);
const allStepsChecked = computed(() =>
  props.active && !isEditForm.value && allStepsDone(instructionList.value.length, disabledSteps.value),
);
watch(allStepsChecked, (done, wasDone) => {
  if (!done || wasDone || !madeThisPrompt.dialogAvailable.value) {
    return;
  }
  madeThisPrompt.requestDialog(true);
});

function sectionTitleLabel(id?: string) {
  return id && showTitleEditor.value[id]
    ? i18n.t("recipe.clear-section")
    : i18n.t("recipe.add-section");
}

function onSectionTitleFocused(id: string | undefined, focused: boolean) {
  if (focused && id && autofocusSectionId.value === id) {
    autofocusSectionId.value = null;
  }
}

function toggleShowTitle(id?: string) {
  if (!id) {
    return;
  }

  const showing = showTitleEditor.value[id];
  if (showing) {
    // the button clears the section rather than just hiding it, so drop the title with it
    const step = instructionList.value.find(element => element.id === id);
    if (step) {
      step.title = "";
    }
  }
  else {
    // the field is rendered by the line below, so ask for focus and let it claim it on mount
    autofocusSectionId.value = id;
  }

  showTitleEditor.value[id] = !showing;

  const temp = { ...showTitleEditor.value };
  showTitleEditor.value = temp;
}

function onDragEnd() {
  drag.value = false;
}

// ===============================================================
// Reference Linker
const activeLinkerIndex = ref(0);
const activeRefs = ref<string[]>([]);
const activeNoteReferenceIds = ref<string[]>([]);
const activeToolReferenceIds = ref<string[]>([]);
const activeText = ref("");
const linkedNotesSheetOpen = ref(false);
const activeStepLinkedNotes = ref<RecipeNote[]>([]);

const availableDialogNextStep = computed(() => activeLinkerIndex.value < instructionList.value.length - 1);
const activeDialogStepText = computed(() => activeText.value);
const linkableTools = computed(() => {
  return (props.recipe.tools ?? []).filter((tool): tool is ToolOut & { id: string } => !!tool.id);
});

const toolsById = computed(() => new Map(linkableTools.value.map(tool => [tool.id, tool])));

function linkedToolsForStep(step: RecipeStep): ToolOut[] {
  return (step.toolReferences ?? [])
    .map(ref => (ref.referenceId ? toolsById.value.get(ref.referenceId) : undefined))
    .filter((tool): tool is ToolOut & { id: string } => tool !== undefined);
}

const linkableNotes = computed(() => {
  return (props.recipe.notes ?? []).filter((note): note is RecipeNote & { referenceId: string } => note.referenceId != null);
});

function openReferenceDialog(idx: number) {
  activeLinkerIndex.value = idx;
  const step = instructionList.value[idx];

  if (!step) {
    activeRefs.value = [];
    activeNoteReferenceIds.value = [];
    activeToolReferenceIds.value = [];
    return;
  }

  activeText.value = step.text;
  activeRefs.value = (step.ingredientReferences ?? []).map(ref => ref.referenceId ?? "");
  activeNoteReferenceIds.value = (step.noteReferences ?? [])
    .map(ref => ref.referenceId)
    .filter((ref): ref is string => ref != null);
  activeToolReferenceIds.value = (step.toolReferences ?? [])
    .map(ref => ref.referenceId)
    .filter((ref): ref is string => ref != null && toolsById.value.has(ref));
  // the groups are built once, so that ticking a reference doesn't move it around
  dialogStepReferences.value = {
    ingredients: new Set(activeRefs.value),
    tools: new Set(activeToolReferenceIds.value),
    notes: new Set(activeNoteReferenceIds.value),
  };
  dialog.value = true;
}

function updateCookModeVisibility() {
  showCookMode.value = false;
  instructionList.value.forEach((element) => {
    if (showCookMode.value === false && element.ingredientReferences && element.ingredientReferences.length > 0) {
      showCookMode.value = true;
    }
  });
}

function saveDialogLinks() {
  const step = instructionList.value[activeLinkerIndex.value];

  if (!step) {
    dialog.value = false;
    return;
  }

  step.ingredientReferences = activeRefs.value.map((referenceId) => {
    return { referenceId };
  });

  step.noteReferences = activeNoteReferenceIds.value.map((referenceId) => {
    return { referenceId };
  });

  step.toolReferences = activeToolReferenceIds.value.map(referenceId => ({ referenceId }));

  updateCookModeVisibility();
  dialog.value = false;
}

function saveAndOpenNextDialogLinks() {
  const currentStepIndex = activeLinkerIndex.value;

  if (!availableDialogNextStep.value) {
    return;
  }

  saveDialogLinks();
  nextTick(() => openReferenceDialog(currentStepIndex + 1));
}

function closeDialog() {
  dialog.value = false;
}

function autoSetReferences() {
  extractIngredientReferences(
    props.recipe.recipeIngredient,
    activeRefs.value,
    activeText.value,
  ).forEach(ingredient => activeRefs.value.push(ingredient));

  toolsMentionedIn(activeText.value, linkableTools.value)
    .filter(id => !activeToolReferenceIds.value.includes(id))
    .forEach(id => activeToolReferenceIds.value.push(id));
}

const noteLookup = computed(() => {
  const results: { [key: string]: string } = {};
  return (props.recipe.notes ?? []).reduce((prev, note) => {
    if (note.referenceId != null) {
      prev[note.referenceId] = note.title;
    }
    return prev;
  }, results);
});

const notesByReferenceId = computed(() => {
  const results: { [key: string]: RecipeNote } = {};
  return (props.recipe.notes ?? []).reduce((prev, note) => {
    if (note.referenceId != null) {
      prev[note.referenceId] = note;
    }
    return prev;
  }, results);
});

function linkedNotesForStep(step: RecipeStep): RecipeNote[] {
  return (step.noteReferences ?? [])
    .map(ref => ref.referenceId ? notesByReferenceId.value[ref.referenceId] : undefined)
    .filter((note): note is RecipeNote => note !== undefined);
}

function openLinkedNotesSheet(step: RecipeStep) {
  activeStepLinkedNotes.value = linkedNotesForStep(step);
  linkedNotesSheetOpen.value = activeStepLinkedNotes.value.length > 0;
}

function hasLinkedIngredients(step: RecipeStep): boolean {
  return !!step.ingredientReferences && step.ingredientReferences.length > 0;
}

function hasLinkedNotes(step: RecipeStep): boolean {
  return linkedNotesForStep(step).length > 0;
}

function hasCookModeLinkedContent(step: RecipeStep): boolean {
  return hasLinkedIngredients(step) || hasLinkedNotes(step);
}

const ingredientLookup = computed(() => {
  const results: { [key: string]: RecipeIngredient } = {};
  return props.recipe.recipeIngredient.reduce((prev, ing) => {
    if (ing.referenceId === undefined) {
      return prev;
    }
    prev[ing.referenceId] = ing;
    return prev;
  }, results);
});

// Map each ingredient's referenceId to its section title
const ingredientSectionTitles = computed(() => {
  const titleMap: { [key: string]: string } = {};
  let currentTitle = "";

  // Go through all ingredients in order
  props.recipe.recipeIngredient.forEach((ingredient) => {
    if (ingredient.referenceId === undefined) {
      return;
    }

    // If this ingredient has a title, update the current title
    if (ingredient.title) {
      currentTitle = ingredient.title;
    }

    // Assign the current title to this ingredient
    titleMap[ingredient.referenceId] = currentTitle;
  });

  return titleMap;
});

interface StepReferences {
  ingredients: Set<string>;
  tools: Set<string>;
  notes: Set<string>;
}

interface LinkGroup {
  key: string;
  label: string | null;
  ingredients: { title: string; ingredients: RecipeIngredient[] }[];
  tools: (ToolOut & { id: string })[];
  notes: (RecipeNote & { referenceId: string })[];
}

interface LinkBlock {
  key: string;
  titleKey: string;
  count: number;
  groups: LinkGroup[];
}

const dialogStepReferences = ref<StepReferences>({ ingredients: new Set(), tools: new Set(), notes: new Set() });

function stepReferences(step: RecipeStep): StepReferences {
  const ids = (refs?: { referenceId?: string | null }[] | null) =>
    new Set((refs ?? []).map(ref => ref.referenceId).filter((id): id is string => !!id));
  return {
    ingredients: ids(step.ingredientReferences),
    tools: ids(step.toolReferences),
    notes: ids(step.noteReferences),
  };
}

function stepLabel(index: number): string {
  const step = instructionList.value[index];
  const label = i18n.t("recipe.step-index", { step: index + 1 });
  return step?.summary ? `${label} — ${step.summary}` : label;
}

// a step always builds on the one right before it, so that one is implied rather than offered,
// and the first step of the recipe has nothing to build on at all
function isStepReferenceAllowed(index: number, referencedIndex: number): boolean {
  return index > 0 && referencedIndex !== -1 && referencedIndex !== index && referencedIndex !== index - 1;
}

function stepReferenceOptions(index: number): { value: string; title: string }[] {
  if (index === 0) {
    return [];
  }
  return instructionList.value
    .map((step, i) => ({ value: step.id ?? "", title: stepLabel(i), index: i }))
    .filter(option => isStepReferenceAllowed(index, option.index) && option.value)
    .map(({ value, title }) => ({ value, title }));
}

// moving a step can turn a reference into the previous step, or the step into the first one
watch(
  () => instructionList.value.map(step => step.id).join(),
  () => {
    const positions = new Map(instructionList.value.map((step, i) => [step.id, i]));
    instructionList.value.forEach((step, index) => {
      const refs = step.stepReferences ?? [];
      const kept = refs.filter(ref => isStepReferenceAllowed(index, positions.get(ref.referenceId) ?? -1));
      if (kept.length !== refs.length) {
        step.stepReferences = kept;
      }
    });
  },
);

function stepReferenceIds(step: RecipeStep): string[] {
  return (step.stepReferences ?? []).map(ref => ref.referenceId).filter((id): id is string => !!id);
}

function setStepReferences(step: RecipeStep, ids: string[] | null) {
  const order = new Map(instructionList.value.map((s, i) => [s.id, i]));
  step.stepReferences = [...new Set(ids ?? [])]
    .sort((a, b) => (order.get(a) ?? 0) - (order.get(b) ?? 0))
    .map(referenceId => ({ referenceId }));
}

function usedStepsForStep(step: RecipeStep): { id: string; label: string }[] {
  return stepReferenceIds(step)
    .map(id => ({ id, index: instructionList.value.findIndex(s => s.id === id) }))
    .filter(used => used.index !== -1 && instructionList.value[used.index] !== step)
    .map(used => ({ id: used.id, label: stepLabel(used.index) }));
}

function linkGroup(
  key: string,
  label: string | null,
  keep: (kind: keyof StepReferences, id: string) => boolean,
): LinkGroup {
  const ingredients: LinkGroup["ingredients"] = [];
  props.recipe.recipeIngredient.forEach((ingredient) => {
    if (!ingredient.referenceId || !keep("ingredients", ingredient.referenceId)) {
      return;
    }
    const title = ingredientSectionTitles.value[ingredient.referenceId] || ingredient.title || "";
    const section = ingredients.find(s => s.title === title);
    if (section) {
      section.ingredients.push(ingredient);
    }
    else {
      ingredients.push({ title, ingredients: [ingredient] });
    }
  });

  return {
    key,
    label,
    ingredients,
    tools: linkableTools.value.filter(tool => keep("tools", tool.id)),
    notes: linkableNotes.value.filter(note => keep("notes", note.referenceId)),
  };
}

function groupSize(group: LinkGroup): number {
  return group.ingredients.reduce((n, s) => n + s.ingredients.length, 0) + group.tools.length + group.notes.length;
}

function linkBlock(key: string, titleKey: string, groups: LinkGroup[]): LinkBlock | null {
  const filled = groups.filter(group => groupSize(group) > 0);
  const count = filled.reduce((n, group) => n + groupSize(group), 0);
  return filled.length ? { key, titleKey, count, groups: filled } : null;
}

/** The references of the dialog: not linked yet, linked to this step, then linked to each other step */
const linkBlocks = computed((): LinkBlock[] => {
  const current = dialogStepReferences.value;
  const others = instructionList.value
    .map((step, index) => ({ index, refs: stepReferences(step) }))
    .filter(({ index }) => index !== activeLinkerIndex.value);
  const linkedElsewhere = (kind: keyof StepReferences, id: string) => others.some(({ refs }) => refs[kind].has(id));

  return [
    linkBlock("unlinked", "recipe.unlinked", [
      linkGroup("unlinked", null, (kind, id) => !current[kind].has(id) && !linkedElsewhere(kind, id)),
    ]),
    linkBlock("this-step", "recipe.linked-to-this-step", [
      linkGroup("this-step", stepLabel(activeLinkerIndex.value), (kind, id) => current[kind].has(id)),
    ]),
    linkBlock("other-steps", "recipe.linked-to-other-step", others.map(({ index, refs }) =>
      linkGroup(`step-${index}`, stepLabel(index), (kind, id) => refs[kind].has(id)),
    )),
  ].filter((block): block is LinkBlock => block !== null);
});

// ===============================================================
// Instruction Merger
const mergeHistory = ref<StepMerge[]>([]);

function mergeAbove(target: number, source: number) {
  const merge = mergeSteps(instructionList.value, target, source);
  if (merge) {
    mergeHistory.value.push(merge);
  }
}

function undoMerge(event: KeyboardEvent) {
  if (!(event.ctrlKey && event.code === "KeyZ")) {
    return;
  }

  const lastMerge = mergeHistory.value.pop();
  if (lastMerge) {
    undoStepMerge(instructionList.value, lastMerge);
  }
}

function moveTo(dest: string, source: number) {
  if (dest === "top") {
    instructionList.value.unshift(instructionList.value.splice(source, 1)[0]);
  }
  else {
    instructionList.value.push(instructionList.value.splice(source, 1)[0]);
  }
}

function insert(dest: number) {
  instructionList.value.splice(dest, 0, { id: uuid4(), text: "", title: "", ingredientReferences: [], noteReferences: [], toolReferences: [], stepReferences: [] });
}

const previewStates = ref<boolean[]>([]);

function togglePreviewState(index: number) {
  const temp = [...previewStates.value];
  temp[index] = !temp[index];
  previewStates.value = temp;
}

function sectionStepIndexes(index: number): number[] {
  const sectionSteps: number[] = [];

  for (let i = index; i < instructionList.value.length; i++) {
    if (!(i === index) && hasSectionTitle(instructionList.value[i].title!)) {
      break;
    }
    else {
      sectionSteps.push(i);
    }
  }
  return sectionSteps;
}

const { $globals } = useNuxtApp();
type StepTimeKey = "durationSeconds" | "coolingSeconds" | "cookingSeconds" | "restSeconds";
const stepTimeFields = computed<{ key: StepTimeKey; icon: string; label: string }[]>(() => [
  { key: "durationSeconds", icon: $globals.icons.knife, label: i18n.t("recipe.step-duration-label") },
  { key: "coolingSeconds", icon: $globals.icons.snowflake, label: i18n.t("recipe.step-cooling-label") },
  { key: "cookingSeconds", icon: $globals.icons.stove, label: i18n.t("recipe.step-cooking-label") },
  { key: "restSeconds", icon: $globals.icons.timerSand, label: i18n.t("recipe.step-rest-label") },
]);

function stepTotalSeconds(step: RecipeStep): number {
  return stepTimeFields.value.reduce((total, field) => total + (step[field.key] ?? 0), 0);
}

function sectionTotalSeconds(index: number): number {
  return sectionStepIndexes(index).reduce((total, i) => total + stepTotalSeconds(instructionList.value[i]), 0);
}

function toggleCollapseSection(index: number) {
  const sectionSteps = sectionStepIndexes(index);

  const allCollapsed = sectionSteps.every(idx => disabledSteps.value.includes(idx));

  if (allCollapsed) {
    disabledSteps.value = disabledSteps.value.filter(idx => !sectionSteps.includes(idx));
  }
  else {
    disabledSteps.value = [...disabledSteps.value, ...sectionSteps];
  }
}

const drag = ref(false);

// ===============================================================
// Image Uploader
const api = useUserApi();

// selecting a word of a step while editing offers to make it a tool of the recipe, linked to the step
const TOOL_SELECTION_MAX_LENGTH = 60;
const toolSelection = ref<{ index: number; text: string } | null>(null);
const creatingTool = ref(false);

function onStepTextSelect(index: number, event: Event) {
  const target = event.target as HTMLTextAreaElement | null;
  if (!target || target.tagName !== "TEXTAREA") {
    return;
  }
  const text = target.value
    .slice(target.selectionStart ?? 0, target.selectionEnd ?? 0)
    .replace(/[*_`#>[\]()]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  toolSelection.value = text && text.length <= TOOL_SELECTION_MAX_LENGTH ? { index, text } : null;
}

async function createToolFromSelection(step: RecipeStep) {
  const selection = toolSelection.value;
  if (!selection) {
    return;
  }
  creatingTool.value = true;
  try {
    const name = selection.text.charAt(0).toUpperCase() + selection.text.slice(1);
    const sameName = (tool: ToolOut) => tool.name.toLocaleLowerCase() === name.toLocaleLowerCase();

    let tool: ToolOut | undefined = (props.recipe.tools ?? []).find(sameName);
    if (!tool) {
      const { data: search } = await api.tools.getAll(1, -1, { search: name });
      tool = search?.items.find(sameName);
    }
    if (!tool) {
      const { data } = await api.tools.createOne({ name });
      tool = data ?? undefined;
    }
    if (!tool?.id) {
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }

    const recipeTools = props.recipe.tools;
    if (recipeTools && !recipeTools.some(t => t.id === tool.id)) {
      recipeTools.push(tool);
    }
    if (!(step.toolReferences ?? []).some(ref => ref.referenceId === tool.id)) {
      step.toolReferences = [...(step.toolReferences ?? []), { referenceId: tool.id }];
    }
    alert.success(i18n.t("recipe.tool-created-from-selection", { name: tool.name }));
    toolSelection.value = null;
  }
  finally {
    creatingTool.value = false;
  }
}
const { recipeAssetPath } = useStaticRoutes();

const loadingStates = ref<{ [key: number]: boolean }>({});

async function handleImageDrop(index: number, files: File[]) {
  if (!files) {
    return;
  }

  // Check if the file is an image
  const file = files[0];
  if (!file || !file.type.startsWith("image/")) {
    return;
  }

  loadingStates.value[index] = true;

  const { data } = await api.recipes.createAsset(props.recipe.slug, {
    name: file.name,
    icon: "mdi-file-image",
    file,
    extension: file.name.split(".").pop() || "",
  });

  loadingStates.value[index] = false;

  if (!data) {
    return; // TODO: Handle error
  }

  embedAsset(index, data);
}

/**
 * Images dragged out of another browser tab carry a URL instead of a file, so the server
 * fetches the image on our behalf.
 */
async function handleImageUrlDrop(index: number, url: string) {
  loadingStates.value[index] = true;

  const { data } = await api.recipes.createAssetFromUrl(props.recipe.slug, url);

  loadingStates.value[index] = false;

  if (!data) {
    alert.error(i18n.t("recipe.failed-to-attach-image"));
    return;
  }

  embedAsset(index, data);
}

/**
 * Some pages render images from blob: urls, which resolve only inside the origin that made
 * them. Nothing can read those bytes from here, so point the user at what does work.
 */
function notifyUnsupportedDrop() {
  alert.error(i18n.t("recipe.image-drop-unsupported"));
}

function embedAsset(index: number, asset: RecipeAsset) {
  emit("update:assets", [...(assets.value ?? []), asset]);
  const assetUrl = recipeAssetPath(props.recipe.id, asset.fileName as string);
  const text = `<img src="${assetUrl}" height="100%" width="100%"/>`;
  instructionList.value[index].text += text;
}

function openImageUpload(index: number) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.onchange = async () => {
    if (input.files) {
      await handleImageDrop(index, Array.from(input.files));
      input.remove();
    }
  };
  input.click();
}
</script>

<style lang="css" scoped>
.thermomix-toggle {
  height: auto !important;
  padding: 4px 10px !important;
  text-transform: none;
}

.thermomix-toggle__label {
  font-size: 0.7rem;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.thermomix-toggle__logo {
  height: 16px;
  width: auto;
  margin-top: 2px;
}

.thermomix-toggle--active {
  background-color: rgba(var(--v-theme-success), 0.08);
}

.thermomix-icon-toggle {
  width: 36px !important;
  min-width: 36px !important;
  height: 36px !important;
  padding: 0 !important;
  overflow: hidden;
}

.thermomix-icon-toggle__image {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: inherit;
}

.thermomix-icon-toggle--active {
  outline: 2px solid rgb(var(--v-theme-success));
  outline-offset: 2px;
}

/* Recipes written for the Thermomix: same look as the toggle, but not an action */
.thermomix-toggle--static {
  cursor: default;
  pointer-events: none;
}

.markdown :deep(.thermomix-setting) {
  display: inline-block;
  padding: 0 8px;
  border-radius: 12px;
  background-color: #00a64f;
  color: #fff;
  font-weight: 600;
  white-space: nowrap;
}

/* In cook mode the buttons are no longer below the title and would touch the scale above */
.cook-mode-actions {
  margin-top: 32px;
}

.cook-mode-button {
  color: #fff !important;
}

.step-times {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
  gap: 2px 10px;
  flex-shrink: 0;
}

.section-total-time {
  margin-left: auto;
  opacity: 1;
}

.grid {
  display: grid;
  gap: 0.5rem;
  height: 100%;
  box-sizing: border-box;

  > * {
    overflow-y: auto;
  }
}

.link-block-title {
  font-size: 1rem;
  font-weight: 700;
}

.link-step-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: rgb(var(--v-theme-primary));
}

.link-type-title {
  font-size: 0.85rem;
  font-weight: 600;
  opacity: 0.75;
}

.link-section-title {
  font-size: 0.8rem;
  font-weight: 600;
  font-style: italic;
}

.sticky {
  position: sticky;
  top: 0;
  z-index: 2;
}

.v-card--link:before {
  background: none;
}

/** Select all li under .markdown class */
.markdown :deep(ul > li) {
  display: list-item;
  list-style-type: disc !important;
}

/** Select all li under .markdown class */
.markdown :deep(ol > li) {
  display: list-item;
}

.flip-list-move {
  transition: transform 0.5s;
}

.no-move {
  transition: transform 0s;
}

.ghost {
  opacity: 0.5;
}

.list-group {
  min-height: 38px;
}

.list-group-item i {
  cursor: pointer;
}

.blur {
  filter: blur(2px);
}

.upload-overlay {
  display: flex;
  justify-content: center;
  align-items: center;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1;
}

.v-text-field :deep(input) {
  font-size: 1.5rem;
}

.v-card-text {
  font-size: 1rem;
}

.recipe-step-title {
  /* Multiline display */
  white-space: normal;
  line-height: 1.25;
  word-break: break-word;
}
.summary-wrapper {
  flex: 1 1 auto;
  min-width: 0; /* wrapping in flex container */
  white-space: normal;
  overflow-wrap: anywhere;
  cursor: pointer;
}
</style>
