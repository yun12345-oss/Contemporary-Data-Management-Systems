<script setup lang="ts">
import { useRoute } from "vue-router";
import QuestionUsage from "../components/QuestionUsage.vue";
const route = useRoute();
</script>
<template>
  <main class="page">
    <router-link to="/questions">← 题目管理</router-link>
    <h1>题目使用追踪</h1>
    <p class="muted">
      展示自己的问卷使用明细；题目所有者可查看按权限提供的外部脱敏使用数量。
    </p>
    <section class="panel phase2-card">
      <QuestionUsage
        :key="String(route.params.id)"
        :question-id="String(route.params.id)"
      />
    </section>
  </main>
</template>
