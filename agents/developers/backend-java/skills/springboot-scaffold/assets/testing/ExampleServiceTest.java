package com.example.service;

import com.example.common.BusinessException;
import com.example.common.ErrorCodeEnum;
import com.example.common.UserContext;
import com.example.pojo.ExampleEntity;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.HashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Service 层单测基线：纯 Mockito，不启 Spring 容器，不连真实 DB / Redis / HTTP。
 * 覆盖正常路径、每条契约错误码路径与边界（空值 / 越界 / 重复提交），清单见 docs/02-protocols/review-criteria.md。
 * UserContext 是 ThreadLocal，必须 @AfterEach 清理，否则用例之间互相污染。
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("示例服务单测")
class ExampleServiceTest {

    @Mock
    private ExampleRepository repository;

    @InjectMocks
    private ExampleService service;

    @AfterEach
    void clearContext() {
        UserContext.remove();
    }

    private void loginAs(long userId, long tenant) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("userId", String.valueOf(userId));
        claims.put("tenant", String.valueOf(tenant));
        UserContext.setUser(claims);
    }

    @Test
    @DisplayName("创建成功：落库带租户，返回雪花 ID 字符串")
    void createSuccess() {
        loginAs(10001L, 2001L);
        when(repository.insert(any(ExampleEntity.class))).thenReturn(1);

        String id = service.create(new ExampleCreateRequest("demo"));

        assertThat(id).isNotBlank();
        verify(repository).insert(any(ExampleEntity.class));
    }

    @Test
    @DisplayName("名称重复：抛 40901，不写库")
    void createConflict() {
        loginAs(10001L, 2001L);
        when(repository.existsByTenantAndName(2001L, "demo")).thenReturn(true);

        assertThatThrownBy(() -> service.create(new ExampleCreateRequest("demo")))
                .isInstanceOf(BusinessException.class)
                .satisfies(e -> assertThat(((BusinessException) e).getCode())
                        .isEqualTo(ErrorCodeEnum.RESOURCE_CONFLICT.getCode()));

        verify(repository, never()).insert(any(ExampleEntity.class));
    }

    @Test
    @DisplayName("未登录上下文：拒绝写入，不允许伪造 tenant=0 落库")
    void createWithoutLogin() {
        assertThatThrownBy(() -> service.create(new ExampleCreateRequest("demo")))
                .isInstanceOf(BusinessException.class);
        verify(repository, never()).insert(any(ExampleEntity.class));
    }
}
