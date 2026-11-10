package com.example.config;

import com.example.web.InternalTokenInterceptor;
import com.example.web.UserContextInterceptor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 微服务拓扑的 MVC 装配：上下文拦截器作用于全部业务路径，内部令牌拦截器只作用于 /internal/**。
 */
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Value("${security.internal-token:}")
    private String internalToken;

    @Bean
    public UserContextInterceptor userContextInterceptor() {
        return new UserContextInterceptor();
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(userContextInterceptor())
                .addPathPatterns("/**")
                .excludePathPatterns("/actuator/**", "/error");

        registry.addInterceptor(new InternalTokenInterceptor(internalToken))
                .addPathPatterns("/internal/**")
                .order(10);
    }
}
