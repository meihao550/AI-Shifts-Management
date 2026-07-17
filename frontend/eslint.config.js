import vue from 'eslint-plugin-vue'
import ts from '@vue/eslint-config-typescript'
import prettier from '@vue/eslint-config-prettier'

export default [
  ...vue.configs['flat/recommended'],
  ...ts(),
  prettier,
  {
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
]
