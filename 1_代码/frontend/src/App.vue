<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { auth, api } from "./api";
import { pendingWork } from "./pending-work";
const router = useRouter(),
  route = useRoute(),
  error = ref("");
async function logout() {
  try {
    if (pendingWork.beforeLogout && !(await pendingWork.beforeLogout())) return;
    await api("/auth/logout", "POST");
    auth.user = null;
    await router.push("/login");
  } catch (e: any) {
    error.value = e.message;
  }
}
</script>
<template>
  <header class="topbar" v-if="route.path != '/login'">
    <router-link to="/" class="brand"
      ><span class="brand-mark">序</span>问序<span class="brand-en"
        >SURVEY LAB</span
      ></router-link
    >
    <nav>
      <router-link to="/" class="nav-link">问卷工作台</router-link
      ><a href="/docs" target="_blank" class="nav-link">接口文档 ↗</a>
    </nav>
    <div class="account">
      <span class="avatar">{{
        auth.user?.username.slice(0, 1).toUpperCase()
      }}</span
      ><span>{{ auth.user?.username }}</span
      ><button class="text-button" @click="logout">退出</button>
    </div>
  </header>
  <div class="global-error" v-if="error">{{ error }}</div>
  <router-view />
  <footer class="site-footer">
    <span>问序 · 让每一个回答有迹可循</span
    ><span>MongoDB 问卷系统 / 第一阶段</span>
  </footer>
</template>
