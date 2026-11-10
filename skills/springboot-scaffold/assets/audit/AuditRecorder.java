package com.example.audit;

import com.example.common.UserContext;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 审计记录写入器（等保二级·安全审计 a/b/c）。
 * 走独立 logger "AUDIT"，由 logback 落到与运行日志分开的文件：混在一起就无法证明记录未被业务日志覆盖。
 * detail 落盘前强制过脱敏；写入失败默认只告警不阻断业务，
 * 要"审计写不成功就拒绝操作"时设 audit.fail-fast=true（由总架构师拍板）。
 */
@Component
public class AuditRecorder {

    private static final Logger AUDIT = LoggerFactory.getLogger("AUDIT");
    private static final Logger log = LoggerFactory.getLogger(AuditRecorder.class);

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String signKey;
    private final boolean failFast;

    public AuditRecorder(@Value("${audit.sign-key:}") String signKey,
                         @Value("${audit.fail-fast:false}") boolean failFast) {
        this.signKey = signKey;
        this.failFast = failFast;
    }

    /** 缺签名密钥仍照常落审计，但记录无法验真，等于放弃 AU-3 防篡改——启动时把这件事说破 */
    @PostConstruct
    void warnIfUnsigned() {
        if (signKey == null || signKey.isBlank()) {
            log.warn("audit.sign-key 未配置：审计记录将以 sign=unsigned 落盘，不满足安全基线 AU-3，生产环境禁止带此配置上线");
        }
    }

    public void record(AuditEventType type, String objectType, String objectId,
                       boolean success, Integer code, String detail) {
        Map<String, Object> event = new LinkedHashMap<>();
        event.put("auditId", nextId());
        event.put("eventTime", OffsetDateTime.now(ZoneId.systemDefault()).toString());
        event.put("actor", actor());
        event.put("eventType", type.name());
        event.put("object", emptyIfNull(objectType) + ":" + emptyIfNull(objectId));
        event.put("outcome", success ? "success" : "fail");
        event.put("code", code);
        event.put("client", client());
        event.put("detail", SensitiveMaskUtils.maskText(detail == null ? "" : detail));
        // 摘要必须对不含 sign 的记录计算：实参先于 put 求值，别改成先塞键再签名
        event.put("sign", sign(event));

        try {
            AUDIT.info(objectMapper.writeValueAsString(event));
        } catch (Exception e) {
            // 审计写入失败绝不静默
            log.error("AUDIT_WRITE_FAILED eventType={} object={} err={}", type, objectType, e.getMessage());
            if (failFast) {
                throw new IllegalStateException("审计记录写入失败，操作已拒绝", e);
            }
        }
    }

    private Map<String, Object> actor() {
        Map<String, Object> actor = new LinkedHashMap<>();
        actor.put("userId", UserContext.getCurrentUserId());
        actor.put("username", UserContext.getUsername() == null ? "anonymous" : UserContext.getUsername());
        actor.put("tenant", UserContext.getCurrentTenant());
        actor.put("role", UserContext.getCurrentRole());
        actor.put("isSysTenant", UserContext.isSysTenant());
        return actor;
    }

    private Map<String, Object> client() {
        Map<String, Object> client = new LinkedHashMap<>();
        client.put("traceId", MDC.get("traceId"));
        ServletRequestAttributes attributes =
                (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (attributes != null) {
            HttpServletRequest request = attributes.getRequest();
            client.put("ip", clientIp(request));
            client.put("userAgent", request.getHeader("User-Agent"));
            client.put("uri", request.getRequestURI());
        }
        return client;
    }

    /** X-Forwarded-For 只取第一段，且可被伪造——审计里当参考值，不作为唯一判定依据 */
    private String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            return forwarded.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    /** 记录级 HMAC，事后检测篡改；配合只增权限的存储账号构成 AU-3 保护措施 */
    private String sign(Map<String, Object> event) {
        if (signKey == null || signKey.isBlank()) {
            return "unsigned";
        }
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(signKey.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] raw = mac.doFinal(objectMapper.writeValueAsString(event).getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(raw.length * 2);
            for (byte b : raw) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (Exception e) {
            log.warn("审计签名失败，记录仍写入但不可验真：{}", e.getMessage());
            return "unsigned";
        }
    }

    private String emptyIfNull(String value) {
        return value == null ? "-" : value;
    }

    /** 雪花 ID：审计记录不允许自增，避免暴露量级并方便跨库合并 */
    private String nextId() {
        return com.baomidou.mybatisplus.core.toolkit.IdWorker.getIdStr();
    }
}
