package com.example.common;

import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serial;
import java.io.Serializable;

/**
 * 统一响应包装：字段名与取值以 docs/02-protocols/api-contract-spec.md 为准。
 */
@Data
@NoArgsConstructor
public class Result<T> implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /** 业务码：200 表示成功，其余必须在契约 x-error-codes 登记 */
    private Integer code;

    /** 契约字段名是 msg，不是 message */
    private String msg;

    private T data;

    private Result(Integer code, String msg, T data) {
        this.code = code;
        this.msg = msg;
        this.data = data;
    }

    public static <T> Result<T> success() {
        return new Result<>(ErrorCodeEnum.SUCCESS.getCode(), ErrorCodeEnum.SUCCESS.getMsg(), null);
    }

    public static <T> Result<T> success(T data) {
        return new Result<>(ErrorCodeEnum.SUCCESS.getCode(), ErrorCodeEnum.SUCCESS.getMsg(), data);
    }

    public static <T> Result<T> fail(String msg) {
        return new Result<>(ErrorCodeEnum.SYSTEM_ERROR.getCode(), msg, null);
    }

    public static <T> Result<T> fail(Integer code, String msg) {
        return new Result<>(code, msg, null);
    }

    /** 失败也要带 data 的场景，如返回校验失败的字段明细 */
    public static <T> Result<T> fail(Integer code, String msg, T data) {
        return new Result<>(code, msg, data);
    }

    public static <T> Result<T> fail(ErrorCodeEnum errorCode) {
        return new Result<>(errorCode.getCode(), errorCode.getMsg(), null);
    }
}
