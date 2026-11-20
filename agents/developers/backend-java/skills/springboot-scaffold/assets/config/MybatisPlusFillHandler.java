package com.example.config;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import com.example.common.UserContext;
import lombok.extern.slf4j.Slf4j;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * 六大基石字段自动填充，字段名与 BaseEntity 对齐：createdAt / updatedAt / createdBy / updatedBy / tenant。
 * insert 用 strictInsertFill，调用方已赋值时不覆盖，便于导入历史数据保留原始创建时间。
 * update 用 setFieldValByName，更新时间每次强制变；用 strict 会留下脏时间。
 * 定时任务、MQ 消费、内部调用等无登录上下文时 userId 为 null，此时跳过填充由 DDL 默认值兜底，禁止伪造 0 冒充系统用户。
 */
@Slf4j
@Component
public class MybatisPlusFillHandler implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        LocalDateTime now = LocalDateTime.now();
        this.strictInsertFill(metaObject, "createdAt", LocalDateTime.class, now);
        this.strictInsertFill(metaObject, "updatedAt", LocalDateTime.class, now);

        Long currentUserId = UserContext.getCurrentUserId();
        if (currentUserId != null) {
            this.strictInsertFill(metaObject, "createdBy", Long.class, currentUserId);
            this.strictInsertFill(metaObject, "updatedBy", Long.class, currentUserId);
        }

        Long tenantId = UserContext.getCurrentTenant();
        if (tenantId != null) {
            this.strictInsertFill(metaObject, "tenant", Long.class, tenantId);
        }
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        this.setFieldValByName("updatedAt", LocalDateTime.now(), metaObject);

        Long currentUserId = UserContext.getCurrentUserId();
        if (currentUserId != null) {
            this.setFieldValByName("updatedBy", currentUserId, metaObject);
        }
    }
}
