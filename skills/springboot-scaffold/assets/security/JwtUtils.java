package com.example.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.Map;

/**
 * JWT 签发与解析（JJWT 0.12.x API：signWith/verifyWith/parseSignedClaims）。
 * 非 Spring Bean：由 JwtConfig 读 JwtProperties 后 new，密钥与有效期集中在配置、不写死代码。
 */
@Slf4j
public class JwtUtils {

    private static final String BEARER_PREFIX = "Bearer ";

    private final SecretKey secretKey;
    private final long expirationMillis;
    private final String issuer;

    public JwtUtils(String secret, long expirationSeconds, String issuer) {
        this.secretKey = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.expirationMillis = expirationSeconds * 1000L;
        this.issuer = issuer;
    }

    public String generateToken(Map<String, Object> claims) {
        Date now = new Date();
        return Jwts.builder()
                .claims(claims)
                .issuer(issuer)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expirationMillis))
                .signWith(secretKey, Jwts.SIG.HS256)
                .compact();
    }

    /** 解析失败返回 null，由调用方翻译成 401xx 错误码 */
    public Claims parseToken(String token) {
        try {
            return Jwts.parser()
                    .requireIssuer(issuer)
                    .verifyWith(secretKey)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (Exception e) {
            log.warn("JWT 解析失败：{}", e.getMessage());
            return null;
        }
    }

    public boolean validateToken(String token) {
        Claims claims = parseToken(token);
        return claims != null && claims.getExpiration() != null
                && claims.getExpiration().after(new Date());
    }

    public String extractTokenFromHeader(String headerValue) {
        if (StringUtils.isBlank(headerValue)) {
            return null;
        }
        return headerValue.startsWith(BEARER_PREFIX)
                ? headerValue.substring(BEARER_PREFIX.length()).trim()
                : headerValue.trim();
    }

    private String claim(String token, String key) {
        Claims claims = parseToken(token);
        return claims == null ? null : String.valueOf(claims.get(key));
    }

    public String getUserId(String token) {
        return claim(token, "userId");
    }

    public String getUsername(String token) {
        return claim(token, "username");
    }

    public String getRole(String token) {
        return claim(token, "role");
    }

    public String getTenant(String token) {
        return claim(token, "tenant");
    }

    public String getSysTenant(String token) {
        return claim(token, "is_sys_tenant");
    }
}
