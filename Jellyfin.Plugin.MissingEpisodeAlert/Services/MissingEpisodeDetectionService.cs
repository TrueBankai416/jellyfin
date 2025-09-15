using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Jellyfin.Data.Enums;
using MediaBrowser.Controller.Entities;
using MediaBrowser.Controller.Entities.TV;
using MediaBrowser.Controller.Library;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.MissingEpisodeAlert.Services;

/// <summary>
/// Service for detecting missing episodes in TV series.
/// </summary>
public class MissingEpisodeDetectionService
{
    private readonly ILibraryManager _libraryManager;
    private readonly ILogger<MissingEpisodeDetectionService> _logger;

    /// <summary>
    /// Initializes a new instance of the <see cref="MissingEpisodeDetectionService"/> class.
    /// </summary>
    /// <param name="libraryManager">The library manager.</param>
    /// <param name="logger">The logger.</param>
    public MissingEpisodeDetectionService(ILibraryManager libraryManager, ILogger<MissingEpisodeDetectionService> logger)
    {
        _libraryManager = libraryManager;
        _logger = logger;
    }

    /// <summary>
    /// Checks if the next episode after the given episode is missing.
    /// </summary>
    /// <param name="currentEpisode">The current episode that just finished playing.</param>
    /// <returns>A task containing information about the missing episode, or null if next episode exists.</returns>
    public async Task<MissingEpisodeInfo?> CheckForMissingNextEpisodeAsync(Episode currentEpisode)
    {
        try
        {
            if (currentEpisode.Series == null)
            {
                _logger.LogWarning("Episode {EpisodeName} has no associated series", currentEpisode.Name);
                return null;
            }

            var series = currentEpisode.Series;
            var currentSeasonNumber = currentEpisode.ParentIndexNumber ?? 0;
            var currentEpisodeNumber = currentEpisode.IndexNumber ?? 0;

            _logger.LogDebug("Checking for missing episode after S{Season}E{Episode} in series {SeriesName}", 
                currentSeasonNumber, currentEpisodeNumber, series.Name);

            // Get all episodes in the current season
            var currentSeasonEpisodes = GetEpisodesInSeason(series, currentSeasonNumber);
            
            // Check if next episode in current season exists
            var nextEpisodeInSeason = currentSeasonEpisodes
                .FirstOrDefault(e => e.IndexNumber == currentEpisodeNumber + 1);

            if (nextEpisodeInSeason != null)
            {
                _logger.LogDebug("Next episode S{Season}E{Episode} exists in series {SeriesName}", 
                    currentSeasonNumber, currentEpisodeNumber + 1, series.Name);
                return null; // Next episode exists
            }

            // Check if there are any episodes after the current one in the same season
            var laterEpisodesInSeason = currentSeasonEpisodes
                .Where(e => e.IndexNumber > currentEpisodeNumber + 1)
                .OrderBy(e => e.IndexNumber)
                .ToList();

            if (laterEpisodesInSeason.Any())
            {
                var nextAvailableEpisode = laterEpisodesInSeason.First();
                var missingEpisodeNumber = currentEpisodeNumber + 1;
                
                _logger.LogInformation("Missing episode detected: S{Season}E{Episode} in series {SeriesName}. Next available is S{Season}E{NextEpisode}", 
                    currentSeasonNumber, missingEpisodeNumber, series.Name, currentSeasonNumber, nextAvailableEpisode.IndexNumber);

                return new MissingEpisodeInfo
                {
                    SeriesName = series.Name,
                    SeasonNumber = currentSeasonNumber,
                    MissingEpisodeNumber = missingEpisodeNumber,
                    NextAvailableEpisode = nextAvailableEpisode,
                    CurrentEpisode = currentEpisode
                };
            }

            // Check if there's a next season with episodes
            var nextSeasonEpisodes = GetEpisodesInSeason(series, currentSeasonNumber + 1);
            if (nextSeasonEpisodes.Any())
            {
                // Check if episode 1 of next season exists
                var nextSeasonFirstEpisode = nextSeasonEpisodes.FirstOrDefault(e => e.IndexNumber == 1);
                if (nextSeasonFirstEpisode != null)
                {
                    _logger.LogDebug("Current season ended normally, next season S{Season}E1 exists in series {SeriesName}", 
                        currentSeasonNumber + 1, series.Name);
                    return null; // Normal season transition
                }

                // Next season exists but episode 1 is missing
                var firstAvailableInNextSeason = nextSeasonEpisodes.OrderBy(e => e.IndexNumber).First();
                
                _logger.LogInformation("Missing episode detected: S{Season}E1 in series {SeriesName}. Next available is S{Season}E{NextEpisode}", 
                    currentSeasonNumber + 1, series.Name, currentSeasonNumber + 1, firstAvailableInNextSeason.IndexNumber);

                return new MissingEpisodeInfo
                {
                    SeriesName = series.Name,
                    SeasonNumber = currentSeasonNumber + 1,
                    MissingEpisodeNumber = 1,
                    NextAvailableEpisode = firstAvailableInNextSeason,
                    CurrentEpisode = currentEpisode
                };
            }

            // Check for episodes in later seasons (cross-season gap detection)
            var laterSeasonEpisodes = GetAllEpisodesAfterSeason(series, currentSeasonNumber);
            if (laterSeasonEpisodes.Any())
            {
                var firstLaterEpisode = laterSeasonEpisodes.First();
                var missingSeasonNumber = currentSeasonNumber + 1;
                
                _logger.LogInformation("Missing entire season detected: S{Season} in series {SeriesName}. Next available is S{Season}E{NextEpisode}", 
                    missingSeasonNumber, series.Name, firstLaterEpisode.ParentIndexNumber, firstLaterEpisode.IndexNumber);

                return new MissingEpisodeInfo
                {
                    SeriesName = series.Name,
                    SeasonNumber = missingSeasonNumber,
                    MissingEpisodeNumber = 1,
                    NextAvailableEpisode = firstLaterEpisode,
                    CurrentEpisode = currentEpisode
                };
            }

            _logger.LogDebug("No more episodes available after S{Season}E{Episode} in series {SeriesName}", 
                currentSeasonNumber, currentEpisodeNumber, series.Name);
            return null; // No more episodes available (series ended)
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error checking for missing episode after {EpisodeName}", currentEpisode.Name);
            return null;
        }
    }

    private List<Episode> GetEpisodesInSeason(Series series, int seasonNumber)
    {
        return _libraryManager.GetItemList(new InternalItemsQuery
        {
            AncestorIds = new[] { series.Id },
            IncludeItemTypes = new[] { BaseItemKind.Episode },
            ParentIndexNumber = seasonNumber,
            IsVirtualItem = false
        }).Cast<Episode>().ToList();
    }

    private List<Episode> GetAllEpisodesAfterSeason(Series series, int currentSeasonNumber)
    {
        return _libraryManager.GetItemList(new InternalItemsQuery
        {
            AncestorIds = new[] { series.Id },
            IncludeItemTypes = new[] { BaseItemKind.Episode },
            IsVirtualItem = false
        }).Cast<Episode>()
        .Where(e => e.ParentIndexNumber.HasValue && e.ParentIndexNumber > currentSeasonNumber)
        .OrderBy(e => e.ParentIndexNumber)
        .ThenBy(e => e.IndexNumber)
        .ToList();
    }
}

/// <summary>
/// Information about a missing episode.
/// </summary>
public class MissingEpisodeInfo
{
    /// <summary>
    /// Gets or sets the series name.
    /// </summary>
    public string SeriesName { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the season number of the missing episode.
    /// </summary>
    public int SeasonNumber { get; set; }

    /// <summary>
    /// Gets or sets the episode number of the missing episode.
    /// </summary>
    public int MissingEpisodeNumber { get; set; }

    /// <summary>
    /// Gets or sets the next available episode.
    /// </summary>
    public Episode? NextAvailableEpisode { get; set; }

    /// <summary>
    /// Gets or sets the current episode that just finished.
    /// </summary>
    public Episode CurrentEpisode { get; set; } = null!;

    /// <summary>
    /// Gets the formatted missing episode identifier.
    /// </summary>
    public string MissingEpisodeIdentifier => $"S{SeasonNumber:D2}E{MissingEpisodeNumber:D2}";
}
