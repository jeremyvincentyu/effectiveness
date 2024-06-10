"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
var eth_crypto_1 = __importDefault(require("eth-crypto"));
process.stdin.on("data", function (data) {
    var private_key = data.toString().trim();
    console.log(eth_crypto_1.default.publicKeyByPrivateKey(private_key));
    process.exit();
});
