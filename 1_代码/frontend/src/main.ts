import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import Login from "./views/Login.vue";
import Dashboard from "./views/Dashboard.vue";
import Editor from "./views/Editor.vue";
import Fill from "./views/Fill.vue";
import Statistics from "./views/Statistics.vue";
import { auth, loadUser } from "./api";
import "./style.css";
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: Login },
    { path: "/", component: Dashboard },
    { path: "/surveys/:id/edit", component: Editor },
    { path: "/survey/:share", component: Fill },
    { path: "/surveys/:id/statistics", component: Statistics },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});
router.beforeEach(async (to) => {
  if (!auth.ready) await loadUser();
  if (!auth.user && to.path != "/login")
    return { path: "/login", query: { next: to.fullPath } };
});
createApp(App).use(router).mount("#app");
