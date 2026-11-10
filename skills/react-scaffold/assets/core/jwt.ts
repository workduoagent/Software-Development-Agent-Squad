/**
 * JWT 载荷解析：只用于刷新页面后恢复用户态展示，不构成鉴权依据。
 * 真实鉴权由后端逐次请求完成，前端结果只可作 UI 层的展示控制。
 */

/** 基础载荷；业务 claims 按接口契约用泛型扩展 */
export interface BaseJwtClaims {
  exp?: number;
  iat?: number;
  [key: string]: unknown;
}

/** 解析 JWT 载荷，不做签名校验；格式非法返回 null */
export function parseTokenClaims<T extends BaseJwtClaims = BaseJwtClaims>(
  token: string | null | undefined,
): T | null {
  if (!token) return null;

  const segments = token.split('.');
  if (segments.length !== 3) return null;

  try {
    // base64url 换回 base64 字符
    const base64 = segments[1].replace(/-/g, '+').replace(/_/g, '/');
    // 补齐 padding，否则 atob 解不了
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');

    const binary = atob(padded);
    // 转 UTF-8，避免中文昵称乱码
    const json = decodeURIComponent(
      binary
        .split('')
        .map((c) => `%${`00${c.charCodeAt(0).toString(16)}`.slice(-2)}`)
        .join(''),
    );

    return JSON.parse(json) as T;
  } catch {
    return null;
  }
}

/**
 * 按 exp 判断 token 是否过期，仅用于前端提前跳登录，不替代后端校验；无 exp 一律视为已过期。
 * 默认预留 30 秒时钟偏移，避免边界时刻误判。
 */
export function isTokenExpired(token: string | null | undefined, offsetSeconds = 30): boolean {
  const claims = parseTokenClaims(token);
  if (!claims?.exp) return true;
  return claims.exp * 1000 - offsetSeconds * 1000 <= Date.now();
}
