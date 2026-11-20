package com.example.audit;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.example.common.BusinessException;
import com.example.common.ErrorCodeEnum;
import com.example.common.UserContext;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.aop.aspectj.annotation.AspectJProxyFactory;
import org.springframework.aop.support.AopUtils;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 审计切面基线单测：CGLIB 与 JDK 动态代理两种形态都要覆盖。
 * 注解只写在实现类上、接口被代理时取不到注解，是这类切面最常见的静默失效。
 */
class AuditLogAspectTest {

    private final ObjectMapper mapper = new ObjectMapper();

    interface UserApi {
        String remove(Long id);
    }

    static class UserService implements UserApi {
        boolean throwSystem;

        @Override
        @AuditLog(type = AuditEventType.DATA_DELETE, object = "User", desc = "删除用户")
        public String remove(Long id) {
            if (throwSystem) {
                throw new IllegalStateException("jdbc url=postgresql://10.0.0.1:5432/prod password=real_pwd");
            }
            if (id == 9L) {
                throw new BusinessException(ErrorCodeEnum.PERMISSION_DENIED, "无权删除该租户外的用户");
            }
            return "ok-" + id;
        }
    }

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

    private UserService cglibProxy(UserService target) {
        AspectJProxyFactory factory = new AspectJProxyFactory(target);
        factory.addAspect(new AuditLogAspect(new AuditRecorder("key", false)));
        factory.setProxyTargetClass(true);
        return factory.getProxy();
    }

    @Test
    void successIsAuditedWithCode200() {
        ListAppender<ILoggingEvent> appender = attachAuditAppender();
        assertEquals("ok-1", cglibProxy(new UserService()).remove(1L));

        JsonNode node = lastEvent(appender);
        assertEquals("DATA_DELETE", node.get("eventType").asText());
        assertEquals("success", node.get("outcome").asText());
        assertEquals(200, node.get("code").asInt());
        assertTrue(node.get("detail").asText().contains("删除用户"));
    }

    @Test
    void deniedOperationIsAuditedWithContractErrorCodeAndRethrown() {
        ListAppender<ILoggingEvent> appender = attachAuditAppender();
        BusinessException thrown = assertThrows(BusinessException.class,
                () -> cglibProxy(new UserService()).remove(9L));

        JsonNode node = lastEvent(appender);
        assertEquals("fail", node.get("outcome").asText(), "被拒绝的操作恰恰是测评要看的部分");
        assertEquals(thrown.getCode().intValue(), node.get("code").asInt());
        assertEquals(40301, node.get("code").asInt());
    }

    @Test
    void systemFailureIsAuditedWithoutLeakingInternals() {
        ListAppender<ILoggingEvent> appender = attachAuditAppender();
        UserService target = new UserService();
        target.throwSystem = true;

        assertThrows(IllegalStateException.class, () -> cglibProxy(target).remove(1L));

        JsonNode node = lastEvent(appender);
        assertTrue(node.get("code").isNull(), "系统异常不发明错误码，交给 GlobalExceptionHandler 归 50001");
        String detail = node.get("detail").asText();
        assertFalse(detail.contains("postgresql://"), detail);
        assertFalse(detail.contains("real_pwd"), detail);
        assertTrue(detail.contains("traceId"), detail);
    }

    @Test
    void annotationOnImplementationMethodStillWorksThroughInterfaceProxy() {
        ListAppender<ILoggingEvent> appender = attachAuditAppender();
        AspectJProxyFactory factory = new AspectJProxyFactory(new UserService());
        factory.addAspect(new AuditLogAspect(new AuditRecorder("key", false)));
        factory.setProxyTargetClass(false);
        UserApi proxy = (UserApi) factory.getProxy();
        assertTrue(AopUtils.isJdkDynamicProxy(proxy), "本用例就是为 JDK 代理形态写的");

        assertEquals("ok-3", proxy.remove(3L));
        assertEquals("success", lastEvent(appender).get("outcome").asText());
    }

    @Test
    void actorComesFromUserContext() {
        ListAppender<ILoggingEvent> appender = attachAuditAppender();
        Map<String, Object> claims = new HashMap<>();
        claims.put("userId", "77");
        claims.put("username", "bob");
        claims.put("tenant", "2");
        UserContext.setUser(claims);

        cglibProxy(new UserService()).remove(5L);
        JsonNode actor = lastEvent(appender).get("actor");
        assertEquals("bob", actor.get("username").asText());
        assertEquals(2, actor.get("tenant").asInt());
    }

    private JsonNode lastEvent(ListAppender<ILoggingEvent> appender) {
        List<ILoggingEvent> events = appender.list;
        assertFalse(events.isEmpty(), "切面没有产生审计记录");
        try {
            return mapper.readTree(events.get(events.size() - 1).getFormattedMessage());
        } catch (Exception e) {
            throw new AssertionError(e);
        }
    }
}
