package com.example.web;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.servlet.HandlerInterceptor;

import java.nio.charset.StandardCharsets;

/**
 * 内部调用令牌拦截器：服务间 Feign 调用不经网关鉴权，靠共享密钥证明来源。
 * 密钥只从配置中心或环境变量注入；缺失时直接拒绝而不放行（fail-closed）。
 */
@Slf4j
public class InternalTokenInterceptor implements HandlerInterceptor {

    public static final String HEADER_INTERNAL_TOKEN = "X-Internal-Token";

    private final String expectedToken;

    public InternalTokenInterceptor(String expectedToken) {
        this.expectedToken = expectedToken;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String token = request.getHeader(HEADER_INTERNAL_TOKEN);
        if (expectedToken == null || expectedToken.isBlank() || !expectedToken.equals(token)) {
            log.warn("内部调用鉴权失败 uri={} remote={}",
                    request.getRequestURI(), request.getRemoteAddr());
            writeUnauthorized(response);
            return false;
        }
        return true;
    }

    private void writeUnauthorized(HttpServletResponse response) {
        try {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json;charset=UTF-8");
            response.getOutputStream().write(
                    "{\"code\":40101,\"msg\":\"内部调用凭证无效\",\"data\":null}"
                            .getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            log.error("写未授权响应失败", e);
        }
    }
}
