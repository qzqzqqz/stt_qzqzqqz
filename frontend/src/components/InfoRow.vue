<template>
  <div class="flex justify-between items-baseline gap-2">
    <span class="text-xs text-on-surface-variant shrink-0">{{ label }}</span>
    <span class="text-sm text-on-surface text-right truncate">{{ value || '—' }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string | number | null | undefined
}>()
</script>