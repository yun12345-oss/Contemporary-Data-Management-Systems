<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, auth } from "../api";
const route = useRoute(),
  router = useRouter(),
  register = ref(false),
  username = ref(""),
  password = ref(""),
  busy = ref(false),
  error = ref("");
async function submit() {
  busy.value = true;
  error.value = "";
  try {
    auth.user = await api(
      `/auth/${register.value ? "register" : "login"}`,
      "POST",
      { username: username.value, password: password.value },
    );
    const next = String(route.query.next || "/");
    await router.push(
      next.startsWith("/") && !next.startsWith("//") ? next : "/",
    );
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <main class="login-layout">
    <section class="login-story">
      <a class="brand light" href="/"
        ><span class="brand-mark">序</span>问序<span class="brand-en"
          >SURVEY LAB</span
        ></a
      >
      <div class="story-content">
        <span class="eyebrow">FROM QUESTIONS TO UNDERSTANDING</span>
        <h1>好的问题，<br />让理解发生。</h1>
        <p>把想知道的变成问题，<br />把每一个回答变成有价值的发现。</p>
        <div class="story-lines">
          <span>01 / 灵活设计</span><span>02 / 条件跳转</span
          ><span>03 / 洞察结果</span>
        </div>
      </div>
      <div class="orbit"><span></span><i></i><b>?</b></div>
      <small>每一次提问，都是一次新的探索。</small>
    </section>
    <section class="login-form-wrap">
      <form @submit.prevent="submit" class="login-form">
        <span class="eyebrow">YOUR RESEARCH STARTS HERE</span>
        <h2>{{ register ? "创建你的账号" : "欢迎回来" }}</h2>
        <p class="muted">
          {{
            register
              ? "开启第一份问卷，让好奇心有处落笔。"
              : "登录工作台，继续你的问卷探索。"
          }}
        </p>
        <label
          >用户名<input
            v-model="username"
            required
            minlength="3"
            maxlength="40"
            autocomplete="username"
            placeholder="至少 3 个字符，支持中文、字母和数字" /></label
        ><label
          >密码<input
            v-model="password"
            type="password"
            required
            minlength="8"
            maxlength="128"
            :autocomplete="register ? 'new-password' : 'current-password'"
            placeholder="至少 8 个字符"
        /></label>
        <div class="alert error" v-if="error" role="alert">{{ error }}</div>
        <button class="button primary full" :disabled="busy">
          {{ busy ? "正在处理…" : register ? "创建账号 →" : "登录工作台 →" }}
        </button>
        <p class="switch-auth">
          {{ register ? "已有账号？" : "还没有账号？" }}
          <button
            type="button"
            class="text-button"
            @click="
              register = !register;
              error = '';
            "
          >
            {{ register ? "立即登录" : "创建账号" }}
          </button>
        </p>
        <div class="login-note">
          账号用于创建问卷与提交回答。<br />问卷允许匿名时，可对创建者隐藏填写身份。
        </div>
      </form>
    </section>
  </main>
</template>
