package com.example.common;

import java.util.HashMap;
import java.util.Map;

/**
 * 当前请求的用户上下文。
 * 数据来源随拓扑不同：单体由 ApiRegisterAspect 解析 JWT 后写入；微服务由网关注入 Header、UserContextInterceptor 写入。
 * 线程池与 JDK 21 虚拟线程复用线程，ThreadLocal 不会自动清理，请求结束必须在 finally 里 remove()，否则跨请求串号。
 */
public final class UserContext {

    private static final ThreadLocal<Map<String, Object>> CONTEXT = new ThreadLocal<>();

    private UserContext() {
    }

    public static void setUser(Map<String, Object> claims) {
        CONTEXT.set(claims == null ? new HashMap<>() : new HashMap<>(claims));
    }

    public static Map<String, Object> getUser() {
        return CONTEXT.get();
    }

    public static void remove() {
        CONTEXT.remove();
    }

    private static Object get(String key) {
        Map<String, Object> claims = CONTEXT.get();
        return claims == null ? null : claims.get(key);
    }

    /** 雪花 ID 在链路中以字符串传递，转 Long 失败时视为未登录 */
    public static Long getCurrentUserId() {
        Object value = get("userId");
        if (value == null) {
            return null;
        }
        try {
            return Long.valueOf(String.valueOf(value));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    public static Long getCurrentTenant() {
        Object value = get("tenant");
        if (value == null) {
            return null;
        }
        try {
            return Long.valueOf(String.valueOf(value));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    public static String getUsername() {
        Object value = get("username");
        return value == null ? null : String.valueOf(value);
    }

    public static String getCurrentRole() {
        Object value = get("role");
        return value == null ? null : String.valueOf(value);
    }

    public static boolean isSysTenant() {
        return "1".equals(String.valueOf(get("is_sys_tenant")));
    }
}
