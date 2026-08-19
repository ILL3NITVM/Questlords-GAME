// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AXFOXRegistry
/// @notice Immutable, read-only public registry identifying the canonical
/// AXFOX token and basic project metadata. This contract has no custody,
/// no trading, no token approvals, no upgrade path, and no privileged
/// financial functionality of any kind — it exists purely so a project
/// identity/version can be looked up on-chain and verified on BscScan.
///
/// Deliberately excluded, by design (not oversight):
/// - no owner/admin role
/// - no withdrawal function
/// - no fallback/receive function (cannot hold BNB)
/// - no token approval/transferFrom calls
/// - no proxy/upgrade pattern
/// - no mutable state after construction
contract AXFOXRegistry {
    address public immutable token;
    string public projectName;
    string public ticker;
    string public version;
    string public officialWebsite;

    constructor(
        address _token,
        string memory _projectName,
        string memory _ticker,
        string memory _version,
        string memory _officialWebsite
    ) {
        require(_token != address(0), "AXFOXRegistry: zero token address");
        token = _token;
        projectName = _projectName;
        ticker = _ticker;
        version = _version;
        officialWebsite = _officialWebsite;
    }
}
