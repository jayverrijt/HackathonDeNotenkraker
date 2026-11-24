<script setup>
    import { computed } from 'vue';
    import { RouterLink, useRoute } from 'vue-router';

    const route = useRoute();

    const isLocationsActive = computed(
    () => route.path === '/' || route.path.startsWith('/locations')
    );

    function handleLogout() {
    // Koppel later aan auth-provider
    console.info('Uitloggen aangeklikt');
}
</script>

<template>
    <header class="sticky top-0 z-30 border-b border-[#E5E5E0] bg-white">
        <div class="mx-auto flex h-16 max-w-[1400px] items-center justify-between px-4 sm:px-6 lg:px-8">
            <div class="flex h-full items-center gap-8">
                <RouterLink
                    to="/"
                    class="text-base font-semibold tracking-tight text-[#1C1D1B] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#1C1D1B]"
                >
                    Gemeente XYZ
                </RouterLink>

                <nav aria-label="Hoofdnavigatie" class="flex h-full items-center">
                    <RouterLink
                        to="/"
                    :class="[
                    'inline-flex h-full items-center border-b-2 px-1 text-sm font-medium transition-colors duration-150',
                    isLocationsActive
                    ? 'border-[#1C1D1B] text-[#1C1D1B]'
                    : 'border-transparent text-[#646660] hover:text-[#1C1D1B]',
                    ]"
                    >
                    Locations
                </RouterLink>
            </nav>
        </div>

        <button
            type="button"
            class="min-h-[44px] rounded-md px-3 text-sm font-medium text-[#646660] transition-colors duration-150 hover:bg-[#F3F3F0] hover:text-[#1C1D1B] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1C1D1B]"
        @click="handleLogout"
        >
        Uitloggen
    </button>
</div>
</header>
</template>