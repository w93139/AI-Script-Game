/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type FusionActionRequest = {
    type: FusionActionRequest.type;
    idempotency_key: string;
    payload?: Record<string, any>;
};
export namespace FusionActionRequest {
    export enum type {
        READY = 'ready',
        ADVANCE_PHASE = 'advance_phase',
        SEND_MESSAGE = 'send_message',
        ASK_QUESTION = 'ask_question',
        SEARCH_LOCATION = 'search_location',
        REVEAL_EVIDENCE = 'reveal_evidence',
        CAST_VOTE = 'cast_vote',
    }
}

