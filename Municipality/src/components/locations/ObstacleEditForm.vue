<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  obstacle: { type: Object, required: true },
  isSaving: { type: Boolean, default: false },
});

const emit = defineEmits(['cancel', 'submit']);

const name = ref(props.obstacle.name);
const error = ref(null);

watch(
  () => props.obstacle.name,
  (newName) => {
    name.value = newName;
  }
);

function handleSubmit() {
  const trimmed = name.value.trim();
  if (!trimmed) {
    error.value = 'Vul een geldige obstakelnaam in.';
    return;
  }

  error.value = null;
  emit('submit', trimmed);
}
</script>

<template>
  <form
    class="overflow-hidden rounded-xl border border-[#E5E5E0] bg-white"
    @submit.prevent="handleSubmit"
  >
    <div class="p-6 sm:p-8">
      <h2 class="text-base font-semibold text-[#1C1D1B]">Obstakelgegevens</h2>
      <p class="mt-1 text-sm text-[#646660]">
        Bewerk de naam van het obstakel en de gegevens van de melding.
      </p>

      <div class="mt-6 space-y-6">
        <div>
          <label for="obstacle-name" class="block text-sm font-medium text-[#1C1D1B]">
            Obstakelnaam
          </label>
          <input
            id="obstacle-name"
            v-model="name"
            type="text"
            required
            class="mt-2 block h-11 w-full rounded-lg border border-[#D4D4CE] bg-white px-3.5 text-sm text-[#1C1D1B] transition-colors focus:border-[#1C1D1B] focus:outline-none"
          />
          <p v-if="error" role="alert" class="mt-1.5 text-xs font-medium text-[#B42318]">
            {{ error }}
          </p>
          <p v-else class="mt-1.5 text-xs text-[#767872]">
            De naam waarmee het obstakel in het overzicht verschijnt.
          </p>
        </div>

        <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div>
            <label for="reporter-uid" class="block text-sm font-medium text-[#1C1D1B]">
              UID van de reporter
            </label>
            <input
              id="reporter-uid"
              type="text"
              :value="obstacle.reporterUid"
              readonly
              aria-readonly="true"
              class="mt-2 block h-11 w-full cursor-not-allowed rounded-lg border border-[#D4D4CE] bg-[#E8E8E4] px-3.5 text-sm font-medium text-[#3F413C] focus:outline-none"
            />
            <p class="mt-1.5 text-xs text-[#767872]">
              Unieke identificatie van de melder.
            </p>
          </div>

          <div>
            <label for="report-date" class="block text-sm font-medium text-[#1C1D1B]">
              Rapportagedatum
            </label>
            <input
              id="report-date"
              type="text"
              :value="obstacle.reportDate"
              readonly
              aria-readonly="true"
              class="mt-2 block h-11 w-full cursor-not-allowed rounded-lg border border-[#D4D4CE] bg-[#E8E8E4] px-3.5 text-sm font-medium tabular-nums text-[#3F413C] focus:outline-none"
            />
            <p class="mt-1.5 text-xs text-[#767872]">DD-MM-JJJJ</p>
          </div>
        </div>
      </div>
    </div>

    <div class="flex flex-col-reverse gap-3 border-t border-[#E5E5E0] bg-[#FAF9F7] px-6 py-4 sm:flex-row sm:justify-end sm:px-8">
      <button
        type="button"
        :disabled="isSaving"
        class="h-11 rounded-lg border border-[#D4D4CE] bg-white px-5 text-sm font-medium text-[#1C1D1B] transition-colors hover:bg-[#F3F3F0] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1C1D1B] disabled:opacity-50"
        @click="emit('cancel')"
      >
        Annuleren
      </button>
      <button
        type="submit"
        :disabled="isSaving"
        class="h-11 rounded-lg bg-[#1C1D1B] px-5 text-sm font-medium text-white transition-colors hover:bg-[#323430] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1C1D1B] disabled:opacity-50"
      >
        {{ isSaving ? 'Opslaan...' : 'Wijzigingen opslaan' }}
      </button>
    </div>
  </form>
</template>
