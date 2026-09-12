/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type PhoneLogin = {
    /**
     * 中国大陆手机号
     */
    phone: string;
    /**
     * 短信验证码
     */
    code: string;
    /**
     * 首次登录邀请码
     */
    invite_code?: (string | null);
    /**
     * 首次登录昵称
     */
    nickname?: (string | null);
};

