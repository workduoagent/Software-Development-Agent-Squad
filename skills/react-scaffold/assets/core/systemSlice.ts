/**
 * 系统主题 Slice：只存「跟随操作系统」的解析结果，由 ThemeProvider 监听 matchMedia 写入，业务代码不得直接改。
 */
import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { ResolvedTheme } from './themeSlice';

export interface SystemState {
  /** 启动时读一次 matchMedia 作初值，之后由 ThemeProvider 的 change 事件更新 */
  resolved: ResolvedTheme;
}

const prefersDark =
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-color-scheme: dark)').matches;

const initialState: SystemState = {
  resolved: prefersDark ? 'dark' : 'light',
};

const systemSlice = createSlice({
  name: 'system',
  initialState,
  reducers: {
    setSystemTheme(state, action: PayloadAction<ResolvedTheme>) {
      state.resolved = action.payload;
    },
  },
});

export const { setSystemTheme } = systemSlice.actions;
export default systemSlice.reducer;
