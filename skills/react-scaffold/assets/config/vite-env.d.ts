/// <reference types="vite/client" />

/** 环境变量类型声明：仅暴露 VITE_ 前缀变量 */
interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string;
  /** 顶栏品牌名，缺省回退到 VITE_APP_TITLE */
  readonly VITE_APP_BRAND?: string;
  readonly VITE_API_BASE_URL: string;
  readonly VITE_BACKEND_ORIGIN?: string;
  /** 'true' 时命中 mock 规则的接口走本地假数据 */
  readonly VITE_USE_MOCK: string;
  readonly VITE_ROUTER_MODE: 'hash' | 'history';
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
