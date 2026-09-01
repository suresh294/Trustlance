const hre = require("hardhat");

async function main() {
    const [deployer] = await hre.ethers.getSigners();

    console.log("Deploying from:", deployer.address);

    // ==========================================
    // 1. Deploy ReputationNFT
    // ==========================================

    console.log("Deploying ReputationNFT...");

    const ReputationNFT =
        await hre.ethers.getContractFactory("ReputationNFT");

    const reputation =
        await ReputationNFT.deploy(deployer.address);

    await reputation.waitForDeployment();

    const reputationAddress =
        await reputation.getAddress();

    console.log("ReputationNFT:", reputationAddress);

    // ==========================================
    // 2. Deploy FreelanceEscrow
    // ==========================================

    console.log("Deploying FreelanceEscrow...");

    const FreelanceEscrow =
        await hre.ethers.getContractFactory("FreelanceEscrow");

    // For development:
    // deployer wallet acts as the trusted score oracle
    const scoreOracleAddress = deployer.address;

    const escrow =
        await FreelanceEscrow.deploy(
            scoreOracleAddress,
            reputationAddress
        );

    await escrow.waitForDeployment();

    const escrowAddress =
        await escrow.getAddress();

    console.log("FreelanceEscrow:", escrowAddress);

    // ==========================================
    // 3. Deployment Summary
    // ==========================================

    console.log("\n=================================");
    console.log("      DEPLOYMENT COMPLETE");
    console.log("=================================");

    console.log("Deployer       :", deployer.address);
    console.log("Score Oracle   :", scoreOracleAddress);
    console.log("Reputation NFT :", reputationAddress);
    console.log("FreelanceEscrow :", escrowAddress);
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});