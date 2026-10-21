// 退出登录前由当前填写页完成保存；页面卸载时解除。
export const pendingWork: { beforeLogout: null | (() => Promise<boolean>) } = {
  beforeLogout: null,
};
