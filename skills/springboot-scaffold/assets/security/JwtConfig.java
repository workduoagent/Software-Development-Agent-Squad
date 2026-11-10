package com.example.security;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.Assert;

@Slf4j
@Configuration
@EnableConfigurationProperties(JwtProperties.class)
public class JwtConfig {

    @Bean
    @ConditionalOnMissingBean
    public JwtUtils jwtUtils(JwtProperties properties) {
        // 启动即校验：弱密钥/缺密钥直接失败，不允许带病上线
        Assert.hasText(properties.getSecret(), "jwt.secret 未配置，请通过环境变量或配置中心注入");
        Assert.isTrue(properties.getSecret().getBytes().length >= 32,
                "jwt.secret 长度不足 32 字节，HS256 不安全");
        log.info("初始化 JwtUtils: expiration={}s, issuer={}", properties.getExpiration(), properties.getIssuer());
        return new JwtUtils(properties.getSecret(), properties.getExpiration(), properties.getIssuer());
    }
}
