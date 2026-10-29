import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import Login from "./views/Login.vue";
import Dashboard from "./views/Dashboard.vue";
import Editor from "./views/Editor.vue";
import Fill from "./views/Fill.vue";
import Statistics from "./views/Statistics.vue";
import Questions from "./views/Questions.vue";
import QuestionEditor from "./views/QuestionEditor.vue";
import QuestionHistory from "./views/QuestionHistory.vue";
import QuestionUsage from "./views/QuestionUsage.vue";
import Libraries from "./views/Libraries.vue";
import Sharing from "./views/Sharing.vue";
import QuestionStatistics from "./views/QuestionStatistics.vue";
import { auth, loadUser } from "./api";
import "./style.css";
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: Login },
    { path: "/", component: Dashboard },
    { path: "/questions", component: Questions },
    { path: "/questions/new", component: QuestionEditor },
    { path: "/questions/:id/edit", component: QuestionEditor },
    { path: "/questions/:id/history", component: QuestionHistory },
    { path: "/questions/:id/usage", component: QuestionUsage },
    { path: "/libraries", component: Libraries },
    { path: "/sharing", component: Sharing },
    {
      path: "/question-versions/:id/statistics",
      component: QuestionStatistics,
    },
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
