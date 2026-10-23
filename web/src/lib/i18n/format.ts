export type Params = Record<string, unknown> | readonly unknown[];

/**
 * Nội suy kiểu printf của Python: `%(name)s`, `%(name)d`, `%s`, `%d`, `%%`.
 * Thiếu tham số thì giữ nguyên placeholder (không ném lỗi, không in "undefined").
 */
export function interpolate(text: string, params?: Params): string {
  if (!params) return text.includes("%%") ? text.replace(/%%/g, "%") : text;
  let positional = 0;
  return text.replace(/%(?:\(([A-Za-z_][\w]*)\))?([sd%])/g, (whole, name: string | undefined, kind: string) => {
    if (kind === "%") return "%";
    let value: unknown;
    if (name !== undefined) {
      if (Array.isArray(params) || !(name in (params as Record<string, unknown>))) return whole;
      value = (params as Record<string, unknown>)[name];
    } else {
      if (!Array.isArray(params) || positional >= params.length) return whole;
      value = params[positional++];
    }
    if (kind === "d") {
      const num = Number(value);
      return Number.isFinite(num) ? String(Math.trunc(num)) : whole;
    }
    return String(value);
  });
}
