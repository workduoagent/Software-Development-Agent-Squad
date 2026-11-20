package com.example.security;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * JWT 配置项（前缀 jwt）。secret 只从环境变量或配置中心注入，禁止写默认值进代码库。
 */
@Getter
@Setter
@ConfigurationProperties(prefix = "jwt")
public class JwtProperties {

    private String secret;

    /** 秒 */
    private long expiration = 7200L;

    private String issuer = "example-app";
}
