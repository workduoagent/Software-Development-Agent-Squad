/**
 * 主题模式 Slice：mode 字段是主题真源，ThemeProvider 解析后写 <html> 的 .light / .dark，
 * 并同步驱动 antd 的 defaultAlgorithm / darkAlgorithm。
 */
import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

/** 用户可选择的主题模式 */
export type ThemeMode = 'light' | 'dark' | 'system';

/** 实际生效的主题（system 已被解析为 light 或 dark） */
export type ResolvedTheme = 'light' | 'dark';

/** localStorage 持久化 key（按项目改前缀，避免同域多应用互相覆盖） */
const STORAGE_KEY = 'app:theme-mode';

export interface ThemeState {
  /** 用户选择的模式，可能是 system */
  mode: ThemeMode;
}

const initialState: ThemeState = {
  mode: (localStorage.getItem(STORAGE_KEY) as ThemeMode | null) ?? 'system',
};

const themeSlice = createSlice({
  name: 'theme',
  initialState,
  reducers: {
    /** 设置主题模式：唯一允许的切换入口 */
    setTheme(state, action: PayloadAction<ThemeMode>) {
      state.mode = action.payload;
      localStorage.setItem(STORAGE_KEY, action.payload);
    },
  },
});

export const { setTheme } = themeSlice.actions;
export default themeSlice.reducer;
