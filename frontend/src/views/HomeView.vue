<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { navItems } from '@/config/nav'
import { maskIconStyle } from '@/utils/icon'
import StarIcon from '@/components/StarIcon.vue'

const auth = useAuthStore()
const themeStore = useThemeStore()

// 一般ユーザーには管理者専用タイルを出さない。ナビ定義は config/nav.ts で共有。
const tiles = computed(() => navItems.filter((t) => !t.adminOnly || auth.isAdmin))
</script>

<template>
  <div class="launcher">
    <RouterLink v-for="t in tiles" :key="t.key" :to="t.to" class="tile">
      <span class="tile__box"><span class="tile__icon nav-ic" :style="maskIconStyle(t.icon)"></span></span>
      <span class="tile__label">{{ t.label }}</span>
    </RouterLink>

    <!-- 星マークで画面を暗転/復帰（ダーク/ライト切替）。遷移せずその場で反映。 -->
    <button type="button" class="tile tile--button" @click="themeStore.toggle()">
      <span class="tile__box">
        <span class="tile__icon">
          <StarIcon :size="40" :filled="themeStore.isDark" />
        </span>
      </span>
      <span class="tile__label">{{ themeStore.isDark ? '明るくする' : '暗くする' }}</span>
    </button>
  </div>
</template>

<style scoped>
/* モックの通り、角丸タイルを3列で並べる。PC では中央寄せ。 */
.launcher {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 22px 16px;
  max-width: 400px;
  margin: 8px auto 0;
}

.tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--ink);
}
/* 星トグルはボタン要素なので既定装飾をリセットしてタイルと揃える。 */
.tile--button {
  background: none;
  border: none;
  cursor: pointer;
  font: inherit;
  padding: 0;
}

.tile__box {
  display: grid;
  place-items: center;
  width: 100%;
  aspect-ratio: 1 / 1;
  background: var(--panel);
  border: 1px solid var(--line-2);
  border-radius: 24px;
  box-shadow: var(--shadow-panel);
  transition: transform 0.12s, border-color 0.12s, box-shadow 0.12s;
}

.tile:hover .tile__box {
  transform: translateY(-2px);
  border-color: var(--indigo);
  box-shadow: 0 4px 14px rgba(25, 28, 24, 0.1);
}

.tile:active .tile__box {
  transform: translateY(0);
}

.tile__icon {
  font-size: 40px;
  line-height: 1;
}
/* マスク画像を currentColor で塗るアイコン（ライト/ダーク両対応）。 */
.nav-ic {
  display: inline-block;
  width: 40px;
  height: 40px;
  background-color: currentColor;
  -webkit-mask-image: var(--nav-ic);
  mask-image: var(--nav-ic);
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
}

.tile__label {
  font-size: 14px;
  font-weight: 600;
  text-align: center;
}
</style>
