<template>
  <div class="flex h-screen bg-surface">
    <AppSidebar />
    <div class="flex-1 flex flex-col min-w-0 ml-64">
      <AppTopbar />
      <main class="flex-1 overflow-auto p-6">
        <div class="max-w-7xl mx-auto">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'
</script>
