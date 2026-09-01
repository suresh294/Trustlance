// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract ReputationNFT is ERC721, Ownable {

    uint256 public nextTokenId;

    struct Reputation {
        uint256 completedJobs;
        uint256 totalAIScore;
    }

    mapping(address => Reputation) public reputation;

    constructor(address initialOwner)
        ERC721("Trustlance Reputation", "TLR")
        Ownable(initialOwner)
    {}

    function mintReputation(
        address freelancer,
        uint256 aiScore
    )
        external
        onlyOwner
    {
        _safeMint(freelancer, nextTokenId);

        reputation[freelancer].completedJobs++;
        reputation[freelancer].totalAIScore += aiScore;

        nextTokenId++;
    }

    function getAverageScore(address freelancer)
        public
        view
        returns(uint256)
    {
        Reputation memory rep = reputation[freelancer];

        if(rep.completedJobs == 0){
            return 0;
        }

        return rep.totalAIScore / rep.completedJobs;
    }

    function _update(
        address to,
        uint256 tokenId,
        address auth
    )
        internal
        override
        returns(address)
    {
        address from = _ownerOf(tokenId);

        if(from != address(0) && to != address(0)){
            revert("Soulbound NFT");
        }

        return super._update(to, tokenId, auth);
    }
}