package com.example.audit;

import java.util.regex.Pattern;

/**
 * 敏感信息脱敏（安全基线 DP-3 / SEC-4）：日志、审计 detail、异常摘要一律先过 maskText，
 * 各处手写拼星号等于没有脱敏。
 * 规则顺序不可调：身份证、手机号、银行卡依次执行，反了长号码会被短规则先吃掉一段；
 * 凭据键值先于 Bearer，否则同一行被两道规则各削一次，输出 "Authorization: *** ***"。
 */
public final class SensitiveMaskUtils {

    private static final Pattern ID_CARD =
            Pattern.compile("(?<=\\D|^)(\\d{6})\\d{8}(\\d{3}[0-9Xx])(?=\\D|$)");
    private static final Pattern PHONE =
            Pattern.compile("(?<=\\D|^)(1[3-9]\\d)\\d{4}(\\d{4})(?=\\D|$)");
    private static final Pattern BANK_CARD =
            Pattern.compile("(?<=\\D|^)(\\d{4})\\d{8,11}(\\d{4})(?=\\D|$)");
    // 值分支：先试引号包裹（JSON），再试「一直到分隔符前的整段」，保证 Authorization: Bearer xxx 这种多段值被一次吃干净
    private static final Pattern CREDENTIAL_VALUE = Pattern.compile(
            "(?i)(\"?)(password|passwd|pwd|token|secret|authorization|x-api-key|access[_-]?key|api[_-]?key)(\"?)\\s*[:=]\\s*(\"[^\"\\\\]*\"|[^,;\\s]+(?:\\s+[^,;\\s]+)*)");
    private static final Pattern BEARER = Pattern.compile("(?i)Bearer\\s+[A-Za-z0-9._\\-]{8,}");

    private SensitiveMaskUtils() {
    }

    /** 自由文本与 JSON 摘要的通用入口 */
    public static String maskText(String text) {
        if (text == null || text.isEmpty()) {
            return text;
        }
        String masked = ID_CARD.matcher(text).replaceAll("$1********$2");
        masked = PHONE.matcher(masked).replaceAll("$1****$2");
        masked = BANK_CARD.matcher(masked).replaceAll("$1********$2");
        masked = CREDENTIAL_VALUE.matcher(masked).replaceAll("$1$2$3: ***");
        masked = BEARER.matcher(masked).replaceAll("Bearer ***");
        return masked;
    }

    public static String maskPhone(String phone) {
        return phone == null || phone.length() < 11 ? "***" : PHONE.matcher(phone).replaceAll("$1****$2");
    }

    public static String maskIdCard(String idCard) {
        return idCard == null || idCard.length() < 15 ? "***" : ID_CARD.matcher(idCard).replaceAll("$1********$2");
    }

    /** 凭据字段永远返回固定掩码：口令没有可展示的合法形态，不保留首尾 */
    public static String maskCredential(String ignored) {
        return "***";
    }
}
