package com.example.aspect;

import java.lang.annotation.*;

/**
 * 单体拓扑的接口声明注解：鉴权、限流、访问日志都由它声明。
 * 语义是默认放行、标注才鉴权，因此漏打注解等于裸奔；Controller 每个 mapping 方法必须有它。
 * 公开接口显式写 requireLogin = false，让评审看出这是决策而不是遗漏。详见 references/topology.md。
 */
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface ApiRegister {

    /** 接口名称，用于日志与审计 */
    String name() default "";

    /** 接口描述，与契约 summary 对齐 */
    String desc() default "";

    boolean requireLogin() default false;

    boolean isLog() default false;

    /** 限流时间窗口（秒） */
    long limitWindow() default 1;

    /** 窗口内最大请求数，0 表示不限流 */
    long limitCount() default 0;
}
