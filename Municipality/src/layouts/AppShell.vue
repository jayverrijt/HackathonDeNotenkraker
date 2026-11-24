<script setup>
import { RouterView } from 'vue-router';
import Navbar from '../components/layout/Navbar.vue';
</script>

<template>
  <div class="min-h-screen bg-[#F7F7F5] text-[#1C1D1B] antialiased">
    <Navbar />
    <main class="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <RouterView />
    </main>
  </div>
</template>
