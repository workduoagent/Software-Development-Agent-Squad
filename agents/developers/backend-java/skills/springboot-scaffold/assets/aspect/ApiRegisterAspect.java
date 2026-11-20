package com.example.aspect;

import com.example.common.BusinessException;
import com.example.common.ErrorCodeEnum;
import com.example.common.UserContext;
import com.example.security.JwtUtils;
import io.jsonwebtoken.Claims;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 单体拓扑的鉴权 + 限流切面。
 * UserContext.remove() 必须在 finally：Tomcat 线程复用与 JDK 21 虚拟线程都会让 ThreadLocal 跨请求残留。
 */
@Slf4j
@Aspect
@Component
public class ApiRegisterAspect {

    @Resource
    private JwtUtils jwtUtils;

    @Resource
    private StringRedisTemplate stringRedisTemplate;

    /** 限流 key 前缀，多实例共用 Redis 时用应用名隔离 */
    @Value("${spring.application.name:app}")
    private String applicationName;

    @Pointcut("@annotation(com.example.aspect.ApiRegister)")
    public void apiRegisterPointcut() {
    }

    @Around("apiRegisterPointcut()")
    public Object around(ProceedingJoinPoint joinPoint) throws Throwable {
        ServletRequestAttributes attributes =
                (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        long startTime = System.currentTimeMillis();
        try {
            if (attributes != null) {
                HttpServletRequest request = attributes.getRequest();
                ApiRegister annotation = resolveAnnotation(joinPoint);
                if (annotation != null) {
                    checkRateLimit(annotation, request);
                    if (annotation.requireLogin()) {
                        UserContext.setUser(parseClaims(request));
                    }
                    if (annotation.isLog()) {
                        log.info("[API] name={} uri={} ip={}",
                                annotation.name(), request.getRequestURI(), request.getRemoteAddr());
                    }
                }
            }
            return joinPoint.proceed();
        } finally {
            UserContext.remove();
            long cost = System.currentTimeMillis() - startTime;
            if (cost > 1000) {
                log.warn("慢请求 cost={}ms method={}", cost, joinPoint.getSignature().toShortString());
            }
        }
    }

    private ApiRegister resolveAnnotation(ProceedingJoinPoint joinPoint) {
        Method method = ((MethodSignature) joinPoint.getSignature()).getMethod();
        return method.getAnnotation(ApiRegister.class);
    }

    private Map<String, Object> parseClaims(HttpServletRequest request) {
        String token = jwtUtils.extractTokenFromHeader(request.getHeader("Authorization"));
        if (token == null || token.isBlank()) {
            throw new BusinessException(ErrorCodeEnum.TOKEN_EMPTY);
        }
        Claims claims = jwtUtils.parseToken(token);
        if (claims == null) {
            throw new BusinessException(ErrorCodeEnum.TOKEN_INVALID);
        }
        Map<String, Object> user = new HashMap<>();
        user.put("userId", claims.get("userId"));
        user.put("username", claims.get("username"));
        user.put("tenant", claims.get("tenant"));
        user.put("role", claims.get("role"));
        user.put("is_sys_tenant", claims.get("is_sys_tenant"));
        return user;
    }

    private void checkRateLimit(ApiRegister annotation, HttpServletRequest request) {
        if (annotation.limitCount() <= 0) {
            return;
        }
        String key = "rate_limit:" + applicationName + ":" + request.getRemoteAddr()
                + ":" + request.getRequestURI();
        Long current = stringRedisTemplate.opsForValue().increment(key);
        if (current != null && current == 1L) {
            stringRedisTemplate.expire(key, annotation.limitWindow(), TimeUnit.SECONDS);
        }
        if (current != null && current > annotation.limitCount()) {
            log.warn("触发限流 key={} current={}", key, current);
            throw new BusinessException(ErrorCodeEnum.API_RATE_LIMIT);
        }
    }
}
