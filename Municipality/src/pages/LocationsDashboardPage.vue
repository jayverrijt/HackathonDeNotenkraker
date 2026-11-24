<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import MapOverview from '../components/locations/MapOverview.vue';
import SavedLocationsList from '../components/locations/SavedLocationsList.vue';
import { obstacleRepository } from '../repositories';

const router = useRouter();

const obstacles = ref([]);
const selectedId = ref(null);
const searchQuery = ref('');
const isLoading = ref(true);

onMounted(async () => {
  try {
    const data = await obstacleRepository.getAll();
    obstacles.value = data;
    selectedId.value = data[0]?.id ?? null;
  } finally {
    isLoading.value = false;
  }
});

const filteredObstacles = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return obstacles.value;
  return obstacles.value.filter(
    (o) =>
      o.name.toLowerCase().includes(q) ||
      o.address.toLowerCase().includes(q)
  );
});

function handleEdit(id) {
  router.push(`/locations/${id}/edit`);
}

async function handleDelete(id) {
  const target = obstacles.value.find((o) => o.id === id);
  if (!target) return;

  const confirmed = window.confirm(
    `Weet je zeker dat je "${target.name}" wilt verwijderen?`
  );
  if (!confirmed) return;

  await obstacleRepository.delete(id);
  obstacles.value = obstacles.value.filter((o) => o.id !== id);
  if (selectedId.value === id) {
    selectedId.value = null;
  }
}
</script>

<template>
  <div>
    <header class="mb-6">
      <p class="text-[11px] font-semibold tracking-wider text-[#767872] uppercase">
        Workspace / Locations
      </p>
      <h1 class="mt-1 text-2xl font-bold tracking-tight text-[#1C1D1B] sm:text-3xl">
        Location dashboard
      </h1>
      <p class="mt-1 text-sm text-[#646660]">
        Manage your places and find them on the map.
      </p>
    </header>

    <div
      v-if="isLoading"
      class="rounded-xl border border-[#E5E5E0] bg-white p-12 text-center text-sm text-[#646660]"
    >
      Locaties laden uit lokale SQLite-database...
    </div>

    <div v-else class="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
      <div class="lg:col-span-7">
        <MapOverview
          :obstacles="filteredObstacles"
          :selected-id="selectedId"
          :area-query="searchQuery"
          @select="selectedId = $event"
          @update:area-query="searchQuery = $event"
        />
      </div>

      <div class="lg:col-span-5">
        <SavedLocationsList
          :obstacles="filteredObstacles"
          :total-count="obstacles.length"
          :selected-id="selectedId"
          :search-query="searchQuery"
          @update:search-query="searchQuery = $event"
          @select="selectedId = $event"
          @edit="handleEdit"
          @delete="handleDelete"
        />
      </div>
    </div>
  </div>
</template>
