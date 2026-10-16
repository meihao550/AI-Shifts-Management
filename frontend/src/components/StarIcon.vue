<script setup lang="ts">
// 星アイコン（idea/icon の星）。filled=true で塗りつぶす（ダークモードON表示などの状態表現に使う）。
// 色は currentColor なので、親の文字色に追従する。
withDefaults(defineProps<{ size?: number; filled?: boolean }>(), {
  size: 22,
  filled: false,
})
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true">
    <path
      d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
      :fill="filled ? 'currentColor' : 'none'"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linejoin="round"
    />
  </svg>
</template>
