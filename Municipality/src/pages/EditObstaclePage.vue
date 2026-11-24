<script setup>
import { onMounted, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { ArrowLeft } from 'lucide-vue-next';
import ObstacleEditForm from '../components/locations/ObstacleEditForm.vue';
import { obstacleRepository } from '../repositories';

const route = useRoute();
const router = useRouter();

const obstacle = ref(null);
const isLoading = ref(true);
const isSaving = ref(false);
const error = ref('');

onMounted(async () => {
  const numericId = Number(route.params.id);
  if (!Number.isFinite(numericId)) {
    router.replace('/');
    return;
  }

  try {
    const found = await obstacleRepository.getById(numericId);
    if (!found) {
      router.replace('/');
      return;
    }
    obstacle.value = found;
  } catch {
    error.value = 'Obstakel ophalen is mislukt. Controleer of de backend draait en vernieuw de pagina.';
  } finally {
    isLoading.value = false;
  }
});

async function handleSave(updatedName) {
  if (!obstacle.value) return;
  isSaving.value = true;
  error.value = '';
  try {
    await obstacleRepository.update(obstacle.value.id, { name: updatedName });
    router.push('/');
  } catch {
    error.value = 'Opslaan is mislukt. Probeer het opnieuw.';
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <p v-if="error" role="alert" class="mx-auto mb-4 max-w-3xl text-sm text-[#B42318]">{{ error }}</p>
  <div
    v-if="isLoading"
    class="mx-auto max-w-3xl rounded-xl border border-[#E5E5E0] bg-white p-12 text-center text-sm text-[#646660]"
  >
    Obstakelgegevens laden...
  </div>

  <div v-else-if="obstacle" class="mx-auto max-w-3xl">
    <RouterLink
      to="/"
      class="inline-flex min-h-[44px] items-center gap-2 text-sm font-medium text-[#646660] transition-colors hover:text-[#1C1D1B] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1C1D1B]"
    >
      <ArrowLeft class="h-4 w-4" />
      Terug naar overzicht
    </RouterLink>

    <header class="mt-2 mb-6">
      <p class="text-[11px] font-semibold tracking-wider text-[#767872] uppercase">
        Workspace / Locations / Bewerken
      </p>
      <h1 class="mt-1 text-2xl font-bold tracking-tight text-[#1C1D1B] sm:text-3xl">
        Obstakel bewerken
      </h1>
      <p class="mt-1 text-sm text-[#646660]">
        Locatie {{ obstacle.id }} · {{ obstacle.address }}
      </p>
    </header>

    <ObstacleEditForm
      :obstacle="obstacle"
      :is-saving="isSaving"
      @cancel="router.push('/')"
      @submit="handleSave"
    />
  </div>
</template>
