package com.example.persistence;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 业务表实体的六大基石字段：id / created_at / updated_at / created_by / updated_by / tenant。
 * 类型、默认值与索引要求见 skills/springboot-scaffold/references/persistence.md 第一节；
 * DDL、实体、填充处理器三处必须同时体现，缺任一项按未完成交付处理。
 * is_deleted 与 version 不是基石字段，只在契约有对应语义时追加。
 * 旧库字段名为 create_at / update_at 时，用 @TableField("create_at") 显式映射，不改契约命名。
 */
@Data
public abstract class BaseEntity implements Serializable {

    /** 雪花 ID：Long 直出在 JS 侧丢精度。ToStringSerializer 只逐字段加，不做全局 Long 转 String，否则数量与时长也变字符串 */
    @TableId(type = IdType.ASSIGN_ID)
    @JsonSerialize(using = ToStringSerializer.class)
    private Long id;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private LocalDateTime createdAt;

    @TableField(value = "updated_at", fill = FieldFill.INSERT_UPDATE)
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private LocalDateTime updatedAt;

    @TableField(value = "created_by", fill = FieldFill.INSERT)
    @JsonSerialize(using = ToStringSerializer.class)
    private Long createdBy;

    @TableField(value = "updated_by", fill = FieldFill.INSERT_UPDATE)
    @JsonSerialize(using = ToStringSerializer.class)
    private Long updatedBy;

    @TableField(value = "tenant", fill = FieldFill.INSERT)
    @JsonSerialize(using = ToStringSerializer.class)
    private Long tenant;
}
