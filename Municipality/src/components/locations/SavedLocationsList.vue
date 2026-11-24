<script setup>
import { Pencil, Search, Trash2 } from 'lucide-vue-next';

defineProps({
  obstacles: { type: Array, required: true },
  totalCount: { type: Number, required: true },
  selectedId: { type: Number, default: null },
  searchQuery: { type: String, default: '' },
});

const emit = defineEmits(['update:searchQuery', 'select', 'edit', 'delete']);
</script>

<template>
  <section
    aria-labelledby="saved-locations-heading"
    class="flex flex-col rounded-xl border border-[#E5E5E0] bg-white"
  >
    <div class="border-b border-[#E5E5E0] p-5">
      <div class="flex items-center gap-2.5">
        <h2 id="saved-locations-heading" class="text-sm font-semibold text-[#1C1D1B]">
          Saved locations
        </h2>
        <span class="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[#F1F1ED] px-1.5 text-xs font-medium tabular-nums text-[#52544E]">
          {{ totalCount }}
        </span>
      </div>

      <div class="relative mt-3.5">
        <label for="locations-search" class="sr-only">Search locations</label>
        <Search
          aria-hidden="true"
          class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#767872]"
        />
        <input
          id="locations-search"
          type="search"
          :value="searchQuery"
          placeholder="Search locations..."
          class="h-10 w-full rounded-lg border border-[#E5E5E0] bg-[#FAF9F7] pl-9 pr-3 text-sm text-[#1C1D1B] placeholder:text-[#8A8C85] transition-colors focus:border-[#1C1D1B] focus:bg-white focus:outline-none"
          @input="emit('update:searchQuery', $event.target.value)"
        />
      </div>
    </div>

    <div class="flex items-center justify-between border-b border-[#E5E5E0] px-5 py-2.5 text-[11px] font-semibold tracking-wider text-[#767872] uppercase">
      <span>Name / Address</span>
      <span>Actions</span>
    </div>

    <ul class="divide-y divide-[#EFEFEA] flex-1">
      <li
        v-if="obstacles.length === 0"
        class="px-5 py-10 text-center text-sm text-[#646660]"
      >
        Geen locaties gevonden voor deze zoekopdracht.
      </li>

      <li
        v-for="(obstacle, index) in obstacles"
        v-else
        :key="obstacle.id"
        :class="[
          'flex items-center justify-between gap-3 px-5 py-3.5 transition-colors duration-150',
          obstacle.id === selectedId ? 'bg-[#F5F5F1]' : 'hover:bg-[#FAF9F7]',
        ]"
      >
        <button
          type="button"
          class="flex min-w-0 flex-1 items-center gap-3.5 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1C1D1B]"
          @click="emit('select', obstacle.id)"
        >
          <span
            :class="[
              'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-medium tabular-nums',
              obstacle.id === selectedId
                ? 'border-[#1C1D1B] bg-[#1C1D1B] text-white'
                : 'border-[#E0E0DA] bg-[#F7F7F5] text-[#52544E]',
            ]"
          >
            {{ index + 1 }}
          </span>
          <span class="min-w-0">
            <span class="block truncate text-sm font-semibold text-[#1C1D1B]">
              {{ obstacle.name }}
            </span>
            <span class="block truncate text-xs text-[#646660]">
              {{ obstacle.address }}
            </span>
          </span>
        </button>

        <div class="flex shrink-0 items-center gap-1">
          <button
            type="button"
            :aria-label="`Bewerk ${obstacle.name}`"
            class="flex h-11 w-11 items-center justify-center rounded-lg text-[#52544E] transition-colors hover:bg-[#EAEAE4] hover:text-[#1C1D1B] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#1C1D1B]"
            @click="emit('edit', obstacle.id)"
          >
            <Pencil class="h-4 w-4" />
          </button>
          <button
            type="button"
            :aria-label="`Verwijder ${obstacle.name}`"
            class="flex h-11 w-11 items-center justify-center rounded-lg text-[#52544E] transition-colors hover:bg-[#FDECEC] hover:text-[#B42318] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#B42318]"
            @click="emit('delete', obstacle.id)"
          >
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      </li>
    </ul>

    <div class="flex items-center justify-between border-t border-[#E5E5E0] px-5 py-3.5 text-xs text-[#767872]">
      <span class="tabular-nums">
        Showing {{ obstacles.length }} of {{ totalCount }} locations
      </span>
      <span>Bewerken op apart scherm</span>
    </div>
  </section>
</template>
