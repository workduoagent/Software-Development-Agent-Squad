package com.example.audit;

import java.lang.annotation.*;

/**
 * 声明式审计：标在 Controller/Service 方法上，由 AuditLogAspect 落记录。
 * AU-1 覆盖面：产生数据变更、数据导出、权限相关行为的接口必须标注。
 * 登录/登出没有用户上下文，改用 AuditRecorder 手工记录。
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface AuditLog {

    AuditEventType type();

    /** 被操作资源类型，如 question / user / apikey */
    String object();

    /** 可读描述，进审计记录 detail 前缀 */
    String desc() default "";

    /** 是否从入参解析资源 ID；导出/删除类事件要留全量证据，保持 true */
    boolean logArgs() default true;
}
