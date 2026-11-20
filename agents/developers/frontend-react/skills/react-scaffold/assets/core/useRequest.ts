/**
 * 页面级异步数据请求 Hook：接口数据统一走这里，不塞进 Redux。
 * 用法：const { data, loading, error, refresh } = useRequest(() => get('/xxx'), []);
 */

import { useCallback, useEffect, useState } from 'react';

/** 依赖项元素放宽，允许标量、函数、函数数组混写 */
type DependOption = void | number | string | boolean | null | undefined | (() => void) | (() => void)[];

export interface UseRequestResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  /** 手动刷新 */
  refresh: () => void;
}

export function useRequest<T>(
  fetcher: () => Promise<T>,
  deps: DependOption[] = [],
): UseRequestResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [reloadFlag, setReloadFlag] = useState(0);

  useEffect(() => {
    // 卸载或依赖变更后丢弃在途请求的回包，避免旧结果覆盖新状态
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetcher()
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err : new Error(String(err)));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadFlag]);

  const refresh = useCallback(() => setReloadFlag((prev) => prev + 1), []);

  return { data, loading, error, refresh };
}
