package com.example.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * MyBatis-Plus 核心配置。
 * 分页方言必须显式写死 DbType.POSTGRE_SQL：靠 URL 推断时，测试库或 H2 会拼出错误分页语句。
 * maxLimit 必须设：pageSize 上限由后端强制，不能只在前端做。
 * 不用 TenantLineInnerInterceptor 自动改写 SQL，它对无 tenant 列的表会生成非法 SQL；
 * 租户条件一律在 QueryWrapper 里显式写，见 references/persistence.md。
 */
@Configuration
public class MybatisPlusConfig {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();

        PaginationInnerInterceptor pagination = new PaginationInnerInterceptor(DbType.POSTGRE_SQL);
        // 请求页超过最大页时不回跳首页，直接返回空列表：避免"翻页越界拿到第一页"的错觉
        pagination.setOverflow(false);
        pagination.setMaxLimit(500L);
        interceptor.addInnerInterceptor(pagination);

        return interceptor;
    }
}
