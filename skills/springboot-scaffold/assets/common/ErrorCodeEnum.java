package com.example.common;

import lombok.Getter;

/**
 * 全局错误码枚举，代码侧唯一真源，必须与契约顶层 x-error-codes 一一对应。
 * 编码规则：HTTP 状态码乘以 100 再加两位序号，细则见 references/infrastructure.md。
 * 新增码必须同步登记契约并出现在对应 operation 的错误样例里，否则 contract_validator 以 E006 / E011 拦截。
 */
@Getter
public enum ErrorCodeEnum {

    SUCCESS(200, "操作成功"),

    PARAM_ERROR(40001, "参数校验失败"),
    REQUEST_BODY_INVALID(40002, "请求体格式错误"),

    TOKEN_INVALID(40101, "凭证无效或已过期"),
    TOKEN_EMPTY(40102, "缺少认证凭证"),
    LOGIN_FAILED(40103, "账号或密码错误"),

    PERMISSION_DENIED(40301, "权限不足，无法操作"),
    TENANT_MISMATCH(40302, "无权访问该租户数据"),

    RESOURCE_NOT_FOUND(40401, "请求资源不存在"),

    RESOURCE_CONFLICT(40901, "资源已存在或状态冲突"),

    API_RATE_LIMIT(42901, "请求过于频繁，请稍后再试"),

    SYSTEM_ERROR(50001, "系统异常，请稍后重试"),
    REMOTE_CALL_ERROR(50002, "下游服务调用失败");

    private final Integer code;
    private final String msg;

    ErrorCodeEnum(Integer code, String msg) {
        this.code = code;
        this.msg = msg;
    }

    public static ErrorCodeEnum getByCode(Integer code) {
        if (code != null) {
            for (ErrorCodeEnum item : values()) {
                if (item.code.equals(code)) {
                    return item;
                }
            }
        }
        return SYSTEM_ERROR;
    }
}
