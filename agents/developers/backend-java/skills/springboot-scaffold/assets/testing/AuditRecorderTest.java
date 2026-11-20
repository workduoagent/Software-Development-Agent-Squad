package com.example.audit;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.example.common.UserContext;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 审计写入器基线单测：证明八要素齐备、脱敏生效、与运行日志物理分离，而不只是证明代码能跑。
 * 字段名一改本用例即失败，用来拦契约漂移。
 */
class AuditRecorderTest {

    private final ObjectMapper mapper = new ObjectMapper();

    @AfterEach
    void cleanup() {
        UserContext.remove();
    }

    private ListAppender<ILoggingEvent> attachAuditAppender() {
        Logger audit = (Logger) LoggerFactory.getLogger("AUDIT");
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        audit.addAppender(appender);
        return appender;
    }

    @Test
    void recordWritesSignedJsonWithAllElements() throws Exception {
        ListAppender<ILoggingEvent> appender = attachAuditAppender();
        Map<String, Object> claims = new HashMap<>();
        claims.put("userId", "10001");
        claims.put("username", "alice");
        claims.put("tenant", "1");
        claims.put("role", "ADMIN");
        UserContext.setUser(claims);

        new AuditRecorder("test-sign-key-32-bytes-long!!!", false)
                .record(AuditEventType.LOGIN_SUCCESS, "User", "10001", true, 200, "手机号 13812345678 登录成功");

        assertEquals(1, appender.list.size());
        JsonNode node = mapper.readTree(appender.list.get(0).getFormattedMessage());
        for (String key : new String[]{"auditId", "eventTime", "actor", "eventType",
                "object", "outcome", "code", "client", "detail", "sign"}) {
            assertTrue(node.has(key), "审计记录缺字段：" + key);
        }
        assertEquals("alice", node.get("actor").get("username").asText());
        assertEquals("User:10001", node.get("object").asText());
        assertEquals("success", node.get("outcome").asText());
        assertEquals(64, node.get("sign").asText().length(), "sign 必须是 HMAC-SHA256 十六进制");
        assertTrue(node.get("detail").asText().contains("138****5678"), node.get("detail").asText());
        assertFalse(node.get("detail").asText().contains("13812345678"), "明文手机号不得进审计");
    }

    @Test
    void anonymousAndUnsignedAreBothExplicit() throws Exception {
        ListAppender<ILoggingEvent> appender = attachAuditAppender();
        new AuditRecorder("", false).record(AuditEventType.LOGIN_FAIL, "Auth", "-", false, 40101, "口令错误");

        JsonNode node = mapper.readTree(appender.list.get(0).getFormattedMessage());
        assertEquals("anonymous", node.get("actor").get("username").asText(), "未登录事件也要能追到人");
        assertTrue(node.get("actor").get("userId").isNull());
        assertEquals("fail", node.get("outcome").asText());
        assertEquals("unsigned", node.get("sign").asText(), "缺签名密钥必须显式标注，不能假装已签名");
    }

    @Test
    void maskCoversEverySensitiveShape() {
        assertEquals("身份证 110101********1234", SensitiveMaskUtils.maskText("身份证 110101199001011234"));
        assertEquals("卡号 6222********0123", SensitiveMaskUtils.maskText("卡号 6222021234567890123"));
        String json = SensitiveMaskUtils.maskText("{\"password\":\"hunter2\",\"token\":\"abc.def\"}");
        assertFalse(json.contains("hunter2"), json);
        assertFalse(json.contains("abc.def"), json);
        assertEquals("Authorization: ***",
                SensitiveMaskUtils.maskText("Authorization: Bearer eyJhbGciOi.abcdef.123"));
        assertEquals("Bearer ***", SensitiveMaskUtils.maskText("Bearer eyJhbGciOi.abcdef.123"));
        assertEquals("***", SensitiveMaskUtils.maskCredential("任何口令都不保留首尾"));
    }

    @Test
    void auditFileIsPhysicallySeparatedFromRuntimeLog() throws Exception {
        String marker = "AUDIT-SEP-" + System.nanoTime();
        new AuditRecorder("k", false).record(AuditEventType.DATA_EXPORT, "User", "1", true, 200,
                marker + " 手机号 13812345678");
        LoggerFactory.getLogger(AuditRecorderTest.class).info(marker + "-runtime");
        // 停止 appender 才会真正落盘，也顺带证明审计没走 AsyncAppender
        ((Logger) LoggerFactory.getLogger("AUDIT")).detachAndStopAllAppenders();
        ((Logger) LoggerFactory.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME)).detachAndStopAllAppenders();

        File auditFile = firstFile("target/test-logs", marker, "-audit.");
        assertNotNull(auditFile, "未生成独立审计文件——检查 logback 的 AUDIT_FILE appender 与 logger AUDIT");
        String auditText = Files.readString(auditFile.toPath(), StandardCharsets.UTF_8);
        assertTrue(auditText.contains(marker) && auditText.contains("138****5678"), "审计行缺失或未脱敏");

        File runtimeFile = firstFile("target/test-logs", marker + "-runtime", null);
        assertNotNull(runtimeFile, "未生成运行日志文件");
        assertFalse(Files.readString(runtimeFile.toPath(), StandardCharsets.UTF_8).contains(marker + "\""),
                "审计记录漏进运行日志，additivity=false 未生效");
    }

    private File firstFile(String dir, String needle, String nameMustContain) throws Exception {
        File[] files = new File(dir).listFiles();
        if (files == null) {
            return null;
        }
        for (File file : files) {
            if (!file.isFile() || (nameMustContain != null && !file.getName().contains(nameMustContain))) {
                continue;
            }
            if (Files.readString(file.toPath(), StandardCharsets.UTF_8).contains(needle)) {
                return file;
            }
        }
        return null;
    }
}
