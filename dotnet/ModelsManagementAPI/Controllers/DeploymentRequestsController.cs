using Microsoft.AspNetCore.Mvc;
using System.ComponentModel.DataAnnotations;
using ModelsManagementAPI.Models;
using ModelsManagementAPI.Services;

namespace ModelsManagementAPI.Controllers;

/// <summary>
/// Manages AI Foundry model deployment requests with approval workflow.
/// </summary>
[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class DeploymentRequestsController : ControllerBase
{
    private readonly IDeploymentRequestService _service;

    public DeploymentRequestsController(IDeploymentRequestService service)
    {
        _service = service;
    }

    /// <summary>
    /// Submit a new model deployment request (Pending approval).
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(ModelDeploymentRequest), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Create([FromBody] CreateDeploymentRequestDto dto)
    {
        var request = new ModelDeploymentRequest
        {
            ModelName = dto.ModelName,
            DeploymentName = dto.DeploymentName,
            ProjectName = dto.ProjectName,
            Region = dto.Region,
            BusinessJustification = dto.BusinessJustification,
            SkuName = dto.SkuName,
            SkuCapacity = dto.SkuCapacity,
            ModelVersion = dto.ModelVersion,
            RequestGroup = dto.RequestGroup,
            RequestUser = dto.RequestUser
        };

        var created = await _service.CreateRequestAsync(request);
        return CreatedAtAction(nameof(GetById), new { id = created.Id, projectName = created.ProjectName }, created);
    }

    /// <summary>
    /// Retrieve all deployment requests.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(IEnumerable<ModelDeploymentRequest>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetAll()
    {
        var requests = await _service.GetAllRequestsAsync();
        return Ok(requests);
    }

    /// <summary>
    /// Retrieve a specific deployment request by ID.
    /// </summary>
    [HttpGet("{id}")]
    [ProducesResponseType(typeof(ModelDeploymentRequest), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetById(string id, [FromQuery, Required] string projectName)
    {
        var request = await _service.GetRequestByIdAsync(id, projectName);
        if (request is null)
            return NotFound();

        return Ok(request);
    }

    /// <summary>
    /// Approve a deployment request and trigger ARM deployment (Admin).
    /// </summary>
    [HttpPut("{id}/approve")]
    [ProducesResponseType(typeof(ModelDeploymentRequest), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Approve(string id, [FromQuery, Required] string projectName, [FromBody] ApproveDeploymentRequestDto dto)
    {
        var request = await _service.GetRequestByIdAsync(id, projectName);
        if (request is null)
            return NotFound();

        if (request.Status != "requested_pending_approval")
            return BadRequest($"Request is already '{request.Status}'. Only requests with status 'requested_pending_approval' can be approved.");

        var updated = await _service.ApproveRequestAsync(id, projectName, dto.ReviewedBy);
        return Ok(updated);
    }

    /// <summary>
    /// Reject a deployment request (Admin).
    /// </summary>
    [HttpPut("{id}/reject")]
    [ProducesResponseType(typeof(ModelDeploymentRequest), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Reject(string id, [FromQuery, Required] string projectName, [FromBody] RejectDeploymentRequestDto dto)
    {
        var request = await _service.GetRequestByIdAsync(id, projectName);
        if (request is null)
            return NotFound();

        if (request.Status != "requested_pending_approval")
            return BadRequest($"Request is already '{request.Status}'. Only requests with status 'requested_pending_approval' can be rejected.");

        var updated = await _service.RejectRequestAsync(id, projectName, dto.ReviewedBy, dto.RejectionReason);
        return Ok(updated);
    }
}
