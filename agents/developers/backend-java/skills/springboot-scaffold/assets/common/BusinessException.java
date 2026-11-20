package com.example.common;

import lombok.Getter;

import java.io.Serial;

/**
 * 业务异常：只用于可预期的失败，由 GlobalExceptionHandler 转成 Result。
 * 不要用它包裹 NPE / IO / SQL 等系统级异常，那类走 Exception 兜底并打 error 日志。
 */
@Getter
public class BusinessException extends RuntimeException {

    @Serial
    private static final long serialVersionUID = 1L;

    private final Integer code;

    public BusinessException(String msg) {
        super(msg);
        this.code = ErrorCodeEnum.SYSTEM_ERROR.getCode();
    }

    public BusinessException(Integer code, String msg) {
        super(msg);
        this.code = code;
    }

    public BusinessException(ErrorCodeEnum errorCode) {
        super(errorCode.getMsg());
        this.code = errorCode.getCode();
    }

    /** 沿用错误码、覆写文案，如把参数校验失败细化到具体字段 */
    public BusinessException(ErrorCodeEnum errorCode, String msg) {
        super(msg);
        this.code = errorCode.getCode();
    }
}
