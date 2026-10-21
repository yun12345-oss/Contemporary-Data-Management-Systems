/** 与后端一致：去除首尾空白后，按 Unicode 码点计数。 */
export function trimText(value: string): string {
  // Python str.strip 的空白集合：不把 ECMAScript 特有的 FEFF 当作空白。
  return value.replace(
    /^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/gu,
    "",
  );
}
export function textLength(value: string): number {
  return Array.from(trimText(value)).length;
}
