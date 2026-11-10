package com.example.exception;

import com.example.common.BusinessException;
import com.example.common.ErrorCodeEnum;
import com.example.common.Result;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.stream.Collectors;

/**
 * 全局异常兜底。
 * SSE（text/event-stream）响应头已发出，此时返回对象给消息转换器会抛 HttpMessageNotWritableException 打断正常流，
 * 所以流式接口必须手工写事件帧并返回 null。
 * 客户端主动断开不是故障，降级为 warn，否则日志被刷屏。
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public Object handleBusinessException(BusinessException e, HttpServletRequest request,
                                          HttpServletResponse response) {
        log.warn("业务异常 uri={} code={} msg={}", request.getRequestURI(), e.getCode(), e.getMessage());
        Result<?> result = Result.fail(e.getCode(), e.getMessage());
        if (isSseRequest(request, response)) {
            return writeSseError(response, result);
        }
        return result;
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Object handleValidationException(MethodArgumentNotValidException e,
                                            HttpServletRequest request, HttpServletResponse response) {
        String detail = e.getBindingResult().getFieldErrors().stream()
                .map(this::formatFieldError)
                .collect(Collectors.joining("; "));
        log.warn("参数校验失败 uri={} detail={}", request.getRequestURI(), detail);
        Result<?> result = Result.fail(ErrorCodeEnum.PARAM_ERROR.getCode(),
                ErrorCodeEnum.PARAM_ERROR.getMsg() + ": " + detail);
        if (isSseRequest(request, response)) {
            return writeSseError(response, result);
        }
        return result;
    }

    /**
     * 按 IOException 父类接客户端中断，避免引用 Tomcat 内部类；
     * Spring Boot 3.4 起可另加 AsyncRequestNotUsableException 分支。
     */
    @ExceptionHandler(IOException.class)
    public void handleClientAbort(IOException e, HttpServletRequest request) {
        // 断开连接类异常：响应流已不可写，只能记日志，不能再尝试写响应体
        log.warn("客户端中断请求 uri={} type={} msg={}",
                request.getRequestURI(), e.getClass().getSimpleName(), e.getMessage());
    }

    @ExceptionHandler(Exception.class)
    public Object handleException(Exception e, HttpServletRequest request, HttpServletResponse response) {
        String traceId = String.valueOf(request.getAttribute("traceId"));
        log.error("系统异常 uri={} traceId={}", request.getRequestURI(), traceId, e);
        Result<?> result = Result.fail(ErrorCodeEnum.SYSTEM_ERROR.getCode(),
                ErrorCodeEnum.SYSTEM_ERROR.getMsg());
        // 真实异常摘要只进日志，不进响应体，避免泄漏内部信息
        if (isSseRequest(request, response)) {
            return writeSseError(response, result);
        }
        return result;
    }

    private String formatFieldError(FieldError error) {
        return error.getField() + ": " + error.getDefaultMessage();
    }

    /** 响应的 Content-Type 或请求的 Accept 声明了 event-stream 时走 SSE 分支 */
    private boolean isSseRequest(HttpServletRequest request, HttpServletResponse response) {
        String contentType = response.getContentType();
        if (contentType != null && contentType.contains(MediaType.TEXT_EVENT_STREAM_VALUE)) {
            return true;
        }
        String accept = request.getHeader("Accept");
        return accept != null && accept.contains(MediaType.TEXT_EVENT_STREAM_VALUE);
    }

    /** 手工写一帧 error 事件后结束流；返回 null 让 Spring 跳过消息转换 */
    private Object writeSseError(HttpServletResponse response, Result<?> result) {
        try {
            response.setStatus(HttpStatus.OK.value());
            response.setContentType(MediaType.TEXT_EVENT_STREAM_VALUE);
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            String payload = "{\"code\":" + result.getCode() + ",\"msg\":\""
                    + result.getMsg().replace("\"", "\\\"") + "\"}";
            response.getOutputStream().write(
                    ("event: error\ndata: " + payload + "\n\n").getBytes(StandardCharsets.UTF_8));
            response.getOutputStream().flush();
        } catch (IOException ex) {
            log.warn("SSE 错误帧写入失败：{}", ex.getMessage());
        }
        return null;
    }
}
