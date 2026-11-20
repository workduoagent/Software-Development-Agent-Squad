package com.example.audit;

/**
 * 审计事件类型枚举：取值必须与 docs/02-protocols/security-baseline.md 第四节 event_type 列出的集合一致。
 * 新增类型要走评审——审计覆盖面是等保测评的核查项。
 */
public enum AuditEventType {

    LOGIN_SUCCESS,
    LOGIN_FAIL,
    LOGOUT,
    PERMISSION_DENIED,
    DATA_CREATE,
    DATA_UPDATE,
    DATA_DELETE,
    DATA_EXPORT,
    AUTH_ISSUE,
    CONFIG_CHANGE,
    SECURITY_BLOCK,
    AUDIT_TAMPER
}
