package com.example.web;

import com.example.common.UserContext;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.HashMap;
import java.util.Map;

/**
 * 微服务拓扑的服务侧上下文拦截器：信任网关，只读 Header，不再解析 JWT。
 * 前提是本服务端口不对外暴露，且网关已覆盖客户端伪造的同名 Header。
 * 网关缺省值（unknown / anonymous / 0 / USER）代表未登录，不能当成真实用户写进上下文，否则审计会记成 tenant=0。
 */
@Slf4j
public class UserContextInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        Map<String, Object> claims = new HashMap<>();
        putIfReal(claims, "userId", request.getHeader("X-User-Id"), "unknown");
        putIfReal(claims, "username", request.getHeader("X-Username"), "anonymous");
        putIfReal(claims, "tenant", request.getHeader("X-Tenant"), "0");
        putIfReal(claims, "role", request.getHeader("X-User-Role"), "USER");
        putIfReal(claims, "is_sys_tenant", request.getHeader("X-Sys-Tenant"), null);
        if (!claims.isEmpty()) {
            UserContext.setUser(claims);
        }
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                Object handler, Exception ex) {
        UserContext.remove();
    }

    private void putIfReal(Map<String, Object> claims, String key, String value, String fallback) {
        if (value != null && !value.isEmpty() && !value.equals(fallback)) {
            claims.put(key, value);
        }
    }
}
