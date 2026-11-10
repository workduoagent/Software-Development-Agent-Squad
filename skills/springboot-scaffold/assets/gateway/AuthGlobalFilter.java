package com.example.gateway;

import com.example.common.ErrorCodeEnum;
import com.example.security.JwtUtils;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * 网关集中鉴权：验签一次，再用 mutate 后的 Header 把身份透传给下游服务。
 * 必须用 request.mutate() 覆盖同名 Header，否则客户端可伪造 X-User-Id 冒充他人。
 * 网关是 WebFlux，阻塞调用要包进 Mono.fromCompletionStage 或 boundedElastic，否则会卡 event-loop。
 * 返回 Mono<Void> 的分支不要挂在 switchIfEmpty 末端：空 Mono 会被当作"无值"继续走 fallback，
 * 已写出的 401 会再被处理一次；改用 Mono.error 加 onErrorResume 分流。
 */
@Slf4j
@Component
public class AuthGlobalFilter implements GlobalFilter, Ordered {

    @Resource
    private JwtUtils jwtUtils;

    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    /** 白名单只放健康检查与登录入口，其余一律要求凭证 */
    private static final List<String> WHITE_LIST = List.of(
            "/actuator/**",
            "/api/v1/auth/login"
    );

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getPath().value();
        if (isWhiteList(path)) {
            return chain.filter(exchange);
        }

        String authHeader = exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        String token = jwtUtils.extractTokenFromHeader(authHeader);
        if (token == null || token.isBlank()) {
            return unauthorized(exchange, ErrorCodeEnum.TOKEN_EMPTY);
        }
        if (!jwtUtils.validateToken(token)) {
            return unauthorized(exchange, ErrorCodeEnum.TOKEN_INVALID);
        }

        ServerHttpRequest mutated = exchange.getRequest().mutate()
                .header("X-User-Id", orDefault(jwtUtils.getUserId(token), "unknown"))
                .header("X-Username", orDefault(jwtUtils.getUsername(token), "anonymous"))
                .header("X-Tenant", orDefault(jwtUtils.getTenant(token), "0"))
                .header("X-User-Role", orDefault(jwtUtils.getRole(token), "USER"))
                .header("X-Sys-Tenant", orDefault(jwtUtils.getSysTenant(token), "0"))
                .build();

        return chain.filter(exchange.mutate().request(mutated).build());
    }

    private Mono<Void> unauthorized(ServerWebExchange exchange, ErrorCodeEnum errorCode) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        String body = "{\"code\":" + errorCode.getCode() + ",\"msg\":\""
                + errorCode.getMsg() + "\",\"data\":null}";
        DataBuffer buffer = response.bufferFactory().wrap(body.getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(buffer));
    }

    private boolean isWhiteList(String path) {
        return WHITE_LIST.stream().anyMatch(pattern -> pathMatcher.match(pattern, path));
    }

    private String orDefault(String value, String fallback) {
        return value != null && !value.isBlank() ? value : fallback;
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 100;
    }
}
